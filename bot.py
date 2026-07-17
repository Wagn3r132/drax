"""
🐕🐕🐕 Drax — Bot Cérbero fofo para Discord (arquivo único, com configuração persistente)

Requisitos:
    pip install discord.py python-dotenv

Configuração (.env na mesma pasta):
    DISCORD_TOKEN=seu_token_aqui

Uso:
    python drax.py

--------------------------------------------------------------------------
ARMAZENAMENTO PERSISTENTE (Railway Volume)
--------------------------------------------------------------------------
O Drax guarda toda a configuração (quais canais usar, quais cargos aparecem
no painel de registro, qual cargo é dado ao aceitar as regras) num arquivo
JSON. Isso é necessário porque, sem um Volume, o sistema de arquivos do
Railway é apagado a cada novo deploy/restart.

Se você já anexou um Volume ao serviço no Railway (Settings > Volumes), ele
cria SOZINHO a variável de ambiente RAILWAY_VOLUME_MOUNT_PATH apontando pro
caminho montado (ex: /data). O Drax detecta essa variável automaticamente e
salva o arquivo de configuração lá dentro — não precisa configurar nada a
mais. Rodando localmente (sem Railway), ele só salva o arquivo na pasta
atual mesmo.

--------------------------------------------------------------------------
ATUALIZAÇÃO AUTOMÁTICA (a cada 1 minuto, sem precisar reiniciar)
--------------------------------------------------------------------------
Enquanto o bot estiver rodando (no Railway ou local), ele resincroniza os
painéis sozinho a cada 1 minuto: recria qualquer cargo que tenha sumido,
corrige cor de cargo desatualizada e atualiza o texto do embed. Não precisa
reiniciar/redeploy pra ver isso acontecer — só precisa o processo estar de pé.

--------------------------------------------------------------------------
COMANDOS (precisam de permissão de administração no servidor)
--------------------------------------------------------------------------
/configurar-canal tipo:<Boas-vindas|Saídas|Regras|Registro> canal:#canal
    -> Define qual canal o Drax usa pra cada função. Fica salvo, e se for o
       canal de Regras ou Registro, o painel já é postado/atualizado ali na hora.

/adicionar-cargo-registro nome:"Gamer" cargo:@Gamer emoji:🎮 grupo:"Diversão"
    -> Adiciona (ou atualiza) uma linha no painel de registro, dentro da categoria
       "grupo" (se omitir, cai em "Geral"). Cada categoria vira sua própria mensagem
       no canal de registro. Quem reagir com esse emoji na mensagem recebe o cargo
       automaticamente (e perde o cargo se tirar a reação depois).

/remover-cargo-registro nome:"Gamer"
    -> Remove uma linha/reação do painel de registro (atualiza na hora também).

/definir-cargo-verificado cargo:@Verificado
    -> Define qual cargo é dado a quem clica em "concordo com as regras".

/ver-configuracao
    -> Mostra a configuração atual (canais e cargos salvos, agrupados por categoria).

/painel-registro e /painel-regras
    -> Forçam um novo post manual dos painéis no canal atual (opcional).

/criar-cargos
    -> Cria na hora, se ainda não existirem no servidor, todos os cargos usados
       no painel de registro e o cargo de verificado. O Drax também faz isso
       sozinho e automaticamente sempre que o painel é sincronizado ou alguém
       clica/reage — esse comando é só pra forçar de uma vez, manualmente.

--------------------------------------------------------------------------
PAINEL DE REGISTRO (estilo Carl — reaction roles, com categorias)
--------------------------------------------------------------------------
O painel de registro não usa mais botões: funciona igual ao reaction-role
clássico do Carl-bot. O Drax posta um embed por CATEGORIA (grupo) — ex:
Cores, Verificação, Pings — listando emoji + cargo, com as reações nativas
do Discord embaixo de cada mensagem. Quem reage ganha o cargo, quem tira a
reação perde o cargo. Se uma categoria sozinha passar de 20 cargos (limite
de reações do Discord numa mensagem), ela é dividida em "parte 1", "parte 2"...

O Drax já vem com os cargos de Cores, Verificação e Pings pré-cadastrados. Se
algum desses cargos (ou o cargo de verificado) ainda não existir no servidor
com o nome exato configurado, o Drax CRIA o cargo automaticamente (acontece
sozinho ao sincronizar o painel, ao clicar/reagir, ou de uma vez com o
comando /criar-cargos) — não precisa mais criar nada na mão antes. Se preferir
usar um cargo que já existe mas com nome levemente diferente, é só rodar
/adicionar-cargo-registro de novo com o nome certo que ele corrige na hora
(sem duplicar cargo).
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

# ============================================================
# TOKEN
# ============================================================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ============================================================
# ARMAZENAMENTO PERSISTENTE DA CONFIGURAÇÃO
# ============================================================
# No Railway, anexar um Volume cria sozinho essa variável apontando pro
# caminho montado. Rodando local, cai na pasta atual mesmo.
DATA_DIR = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
ARQUIVO_CONFIG = Path(DATA_DIR) / "drax_config.json"

# Configuração usada apenas na primeira vez que o bot roda (antes de existir
# o arquivo salvo). Depois disso, tudo é editado pelos comandos no Discord.
CONFIG_PADRAO = {
    "canal_boas_vindas_id": 1527366588762951701,
    "canal_saidas_id": 1527366588762951702,
    "canal_regras_id": 1527366588762951704,
    "canal_registro_id": 1527394849953681541,
    "cargo_verificado": "Verificado",
    "cargos_registro": {
        # --- Cores ---
        "Vermelho": {"cargo": "『❤️』Vermelho", "emoji": "❤️", "grupo": "Cores"},
        "Laranja": {"cargo": "『🧡』Laranja", "emoji": "🧡", "grupo": "Cores"},
        "Amarelo": {"cargo": "『💛』Amarelo", "emoji": "💛", "grupo": "Cores"},
        "Verde": {"cargo": "『💚』Verde", "emoji": "💚", "grupo": "Cores"},
        "Azul": {"cargo": "『💙』Azul", "emoji": "💙", "grupo": "Cores"},
        "Roxo": {"cargo": "『💜』Roxo", "emoji": "💜", "grupo": "Cores"},
        "Preto": {"cargo": "『🖤』Preto", "emoji": "🖤", "grupo": "Cores"},
        "Branco": {"cargo": "『🤍』Branco", "emoji": "🤍", "grupo": "Cores"},
        # --- Verificação ---
        "Menino": {"cargo": "『🚹』Menino", "emoji": "🚹", "grupo": "Verificação"},
        "Menina": {"cargo": "『🚺』Menina", "emoji": "🚺", "grupo": "Verificação"},
        "-18": {"cargo": "『🧒』-18", "emoji": "🧒", "grupo": "Verificação"},
        "+18": {"cargo": "『🔞』+18", "emoji": "🔞", "grupo": "Verificação"},
        "Computador": {"cargo": "『💻』Computador", "emoji": "💻", "grupo": "Verificação"},
        "Celular": {"cargo": "『📱』Celular", "emoji": "📱", "grupo": "Verificação"},
        # --- Pings ---
        "Ping Votação": {"cargo": "『🗳️』Ping Votação", "emoji": "🗳️", "grupo": "Pings"},
        "Ping Jornal": {"cargo": "『📰』Ping Jornal", "emoji": "📰", "grupo": "Pings"},
        "Ping Avisos": {"cargo": "『🚨』Ping Avisos", "emoji": "🚨", "grupo": "Pings"},
        "Ping Parceria": {"cargo": "『🤝』Ping Parceria", "emoji": "🤝", "grupo": "Pings"},
        "Tweeter": {"cargo": "『🐦』Tweeter", "emoji": "🐦", "grupo": "Pings"},
        "Instagram": {"cargo": "『📸』Instagram", "emoji": "📸", "grupo": "Pings"},
        "Twitch": {"cargo": "『👾』Twitch", "emoji": "👾", "grupo": "Pings"},
        "Videos Novos": {"cargo": "『🎥』Videos Novos", "emoji": "🎥", "grupo": "Pings"},
        "Fantasma": {"cargo": "『👻』Fantasma", "emoji": "👻", "grupo": "Pings"},
        "Cadeia": {"cargo": "『⛓️』Cadeia", "emoji": "⛓️", "grupo": "Pings"},
        "Mute": {"cargo": "『😶』Mute", "emoji": "😶", "grupo": "Pings"},
    },
    "mensagens_registro": [],  # IDs das mensagens do painel de registro (uma por "parte")
    "texto_regras": (
        "1️⃣ Respeite todo mundo, sem exceções.\n"
        "2️⃣ Nada de spam, flood ou propaganda sem permissão.\n"
        "3️⃣ Proibido conteúdo NSFW.\n"
        "4️⃣ Sem discurso de ódio ou preconceito.\n"
        "5️⃣ Siga os Termos de Serviço do Discord."
    ),
}


def carregar_config() -> dict:
    if ARQUIVO_CONFIG.exists():
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                salvo = json.load(f)
            # mescla com o padrão, assim campos novos adicionados no código no futuro
            # não quebram uma configuração salva antiga
            cfg = {**CONFIG_PADRAO, **salvo}
            cfg["cargos_registro"] = salvo.get("cargos_registro", CONFIG_PADRAO["cargos_registro"])
            cfg["mensagens_registro"] = salvo.get("mensagens_registro", [])
            return cfg
        except Exception as e:
            print(f"⚠️ Não consegui ler {ARQUIVO_CONFIG}, usando configuração padrão. Erro: {e}")
    return json.loads(json.dumps(CONFIG_PADRAO))  # cópia profunda do padrão


def salvar_config():
    ARQUIVO_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"💾 Configuração salva em {ARQUIVO_CONFIG}")


config = carregar_config()

# Cor lateral dos embeds (tema "fogo do submundo")
COR_EMBED = 0xFF6A00

logging.basicConfig(level=logging.INFO)

# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.members = True          # necessário para on_member_join / on_member_remove
intents.message_content = True  # útil caso queira comandos de prefixo no futuro

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ============================================================
# PAINEL DE REGISTRO — estilo Carl (reaction roles)
# ============================================================
MAX_REACOES_POR_MENSAGEM = 20  # limite do Discord pra reações diferentes numa mensagem


# ============================================================
# CRIAÇÃO AUTOMÁTICA DE CARGOS
# ============================================================
# Cores sugeridas pros cargos padrão de "Cores" (chave = nome cadastrado em
# CONFIG_PADRAO, não o texto completo com colchete/emoji do cargo em si).
CORES_CARGOS_PADRAO = {
    "Vermelho": discord.Color.red(),
    "Laranja": discord.Color.orange(),
    "Amarelo": discord.Color.gold(),
    "Verde": discord.Color.green(),
    "Azul": discord.Color.blue(),
    "Roxo": discord.Color.purple(),
    # Preto "puro" (ou bem escuro) fica INVISÍVEL no tema escuro do Discord —
    # o texto do nome/menção fica quase-preto em cima de um fundo quase-preto.
    # Por isso deixamos sem cor customizada: some pro cinza/branco padrão do
    # tema, que pelo menos é legível.
    "Preto": discord.Color.default(),
    "Branco": discord.Color.from_rgb(245, 245, 245),
}


async def garantir_cargo(
    guild: discord.Guild,
    nome_cargo: str,
    cor: Optional[discord.Color] = None,
    mentionable: bool = False,
) -> Optional[discord.Role]:
    """Procura um cargo pelo nome exato no servidor; se ele não existir, o Drax
    cria na hora. É por isso que os botões/reações não estavam dando os cargos:
    se o nome salvo não bate 100% com nenhum cargo do servidor, antes o Drax só
    desistia em silêncio (ou avisava e não fazia nada)."""
    cargo = discord.utils.get(guild.roles, name=nome_cargo)
    if cargo is not None:
        return cargo
    try:
        cargo = await guild.create_role(
            name=nome_cargo,
            color=cor or discord.Color.default(),
            mentionable=mentionable,
            reason="Drax: cargo criado automaticamente (não existia no servidor)",
        )
        print(f"🐾 Cargo '{nome_cargo}' não existia em '{guild.name}' — criei ele automaticamente.")
        return cargo
    except discord.Forbidden:
        print(f"⚠️ Sem permissão pra criar o cargo '{nome_cargo}'. Dê 'Gerenciar Cargos' ao Drax "
              f"(e confira se o cargo dele está numa posição alta o bastante na hierarquia).")
        return None
    except discord.HTTPException as e:
        print(f"⚠️ Erro ao criar o cargo '{nome_cargo}': {e}")
        return None


async def garantir_todos_cargos_registro(guild: discord.Guild) -> list:
    """Garante (criando se faltar) todos os cargos usados no painel de registro
    atual, e corrige a cor de cargos que já existem mas ficaram com a cor
    desatualizada (ex: o Preto que antes era criado quase-invisível). Retorna
    a lista de nomes que precisaram ser criados agora."""
    criados = []
    for nome, dados in config["cargos_registro"].items():
        cargo_existente = discord.utils.get(guild.roles, name=dados["cargo"])
        cor = CORES_CARGOS_PADRAO.get(nome)
        mencionavel = dados.get("grupo") == "Pings"

        if cargo_existente is not None:
            if cor is not None and cargo_existente.color.value != cor.value:
                try:
                    await cargo_existente.edit(color=cor, reason="Drax: corrigindo cor do cargo")
                except discord.HTTPException:
                    pass
            continue

        cargo = await garantir_cargo(guild, dados["cargo"], cor=cor, mentionable=mencionavel)
        if cargo:
            criados.append(dados["cargo"])
    return criados


def dividir_em_blocos(cargos: list, tamanho: int = MAX_REACOES_POR_MENSAGEM) -> list:
    """Quebra a lista de cargos em blocos de até `tamanho` itens (1 bloco = 1 mensagem)."""
    return [cargos[i:i + tamanho] for i in range(0, len(cargos), tamanho)] or [[]]


def agrupar_cargos(cargos: list) -> dict:
    """Agrupa os cargos por 'grupo' (ex: Cores, Verificação, Pings), preservando a
    ordem em que foram cadastrados. Cargos sem grupo definido caem em 'Geral'."""
    grupos: dict = {}
    for texto, dados in cargos:
        nome_grupo = dados.get("grupo") or "Geral"
        grupos.setdefault(nome_grupo, []).append((texto, dados))
    return grupos


def montar_embed_registro(
    guild: Optional[discord.Guild],
    nome_grupo: str,
    bloco: list,
    indice: int,
    total: int,
    mostrar_intro: bool,
) -> discord.Embed:
    linhas = []
    for _texto, dados in bloco:
        cargo_obj = discord.utils.get(guild.roles, name=dados["cargo"]) if guild else None
        if guild and cargo_obj is None:
            print(f"⚠️ Cargo '{dados['cargo']}' não encontrado no servidor '{guild.name}'. "
                  f"Confira se o nome bate certinho (maiúsculas, espaços, colchetes) ou corrija com /adicionar-cargo-registro.")
        cargo_txt = cargo_obj.mention if cargo_obj else f"@{dados['cargo']}"
        linhas.append(f"{dados['emoji']}  {cargo_txt}")

    titulo = f"🐕🐕🐕 {nome_grupo}" + (f" (parte {indice + 1})" if total > 1 else "")
    intro = (
        "Oi! Eu sou o **Drax**, seu Cérbero fofo de três cabeças guardando esse servidor!\n\n"
        "Reaja com o emoji correspondente pra pegar o cargo. Tire a reação pra perder o cargo. Au au! 🐾\n\n"
        if mostrar_intro else ""
    )

    embed = discord.Embed(
        title=titulo,
        description=intro + ("\n".join(linhas) if linhas else "_nenhum cargo configurado ainda_"),
        color=COR_EMBED,
    )
    if total > 1:
        embed.set_footer(text=f"Parte {indice + 1} de {total} — o Discord só permite 20 reações por mensagem")
    return embed


async def sincronizar_reacoes(mensagem: discord.Message, bloco: list):
    """Garante que a mensagem tenha exatamente as reações do bloco, na ordem certa,
    sem apagar as reações de quem já reagiu nos emojis que continuam no painel."""
    desejadas = [dados["emoji"] for _texto, dados in bloco]
    atuais = {str(r.emoji): r for r in mensagem.reactions}

    for emoji_str in atuais:
        if emoji_str not in desejadas:
            try:
                await mensagem.clear_reaction(emoji_str)
            except discord.HTTPException:
                pass

    for emoji in desejadas:
        if emoji not in atuais:
            try:
                await mensagem.add_reaction(emoji)
            except discord.HTTPException as e:
                print(f"⚠️ Não consegui reagir com {emoji}: {e}")


async def sincronizar_paineis_registro(canal: Optional[discord.TextChannel], recriar: bool = False):
    """Cria ou atualiza as mensagens do painel de registro: uma (ou mais, se passar de
    20 cargos) mensagem por grupo — Cores, Verificação, Pings etc."""
    if canal is None:
        print("⚠️ Canal de registro não encontrado. Confira o ID configurado (/ver-configuracao) e o acesso do Drax a ele.")
        return

    await garantir_todos_cargos_registro(canal.guild)

    grupos = agrupar_cargos(list(config["cargos_registro"].items()))
    ids_atuais = [] if recriar else list(config.get("mensagens_registro", []))
    novas_ids = []
    cursor = 0
    primeiro_bloco_geral = True

    for nome_grupo, itens in grupos.items():
        blocos = dividir_em_blocos(itens)
        for indice, bloco in enumerate(blocos):
            embed = montar_embed_registro(canal.guild, nome_grupo, bloco, indice, len(blocos), primeiro_bloco_geral)
            primeiro_bloco_geral = False

            if cursor < len(ids_atuais):
                try:
                    msg = await canal.fetch_message(ids_atuais[cursor])
                    await msg.edit(embed=embed)
                    await sincronizar_reacoes(msg, bloco)
                    novas_ids.append(msg.id)
                    cursor += 1
                    continue
                except discord.NotFound:
                    pass

            msg = await canal.send(embed=embed)
            await sincronizar_reacoes(msg, bloco)
            novas_ids.append(msg.id)
            cursor += 1

    # apaga mensagens antigas que sobraram (ex: cargos foram removidos e agora precisa de menos partes)
    for id_sobrando in ids_atuais[cursor:]:
        try:
            msg_antiga = await canal.fetch_message(id_sobrando)
            await msg_antiga.delete()
        except discord.NotFound:
            pass

    config["mensagens_registro"] = novas_ids
    salvar_config()
    print(f"🐾 Painel de registro sincronizado em #{canal.name} ({len(novas_ids)} mensagem(ns), {len(grupos)} grupo(s)).")


# ============================================================
# BOTÃO E VIEW — painel de regras (verificação)
# ============================================================
class BotaoAceitarRegras(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Eu concordo com as regras",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id="drax_aceitar_regras",
        )

    async def callback(self, interaction: discord.Interaction):
        cargo = await garantir_cargo(interaction.guild, config["cargo_verificado"])
        if cargo is None:
            await interaction.response.send_message(
                f"🐾 Não consegui achar nem criar o cargo **{config['cargo_verificado']}**. "
                f"Confira se o Drax tem a permissão 'Gerenciar Cargos' e se o cargo dele "
                f"está numa posição alta o suficiente na hierarquia de cargos do servidor.",
                ephemeral=True,
            )
            return

        if cargo in interaction.user.roles:
            await interaction.response.send_message("Você já tá verificado(a)! 🐕", ephemeral=True)
            return

        await interaction.user.add_roles(cargo, reason="Drax: aceitou as regras")
        await interaction.response.send_message(
            "🎉 Show! Agora você já pode explorar o servidor todo. Au au!", ephemeral=True
        )


class PainelRegras(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BotaoAceitarRegras())


# ============================================================
# EMBEDS DOS PAINÉIS
# ============================================================
def montar_embed_regras() -> discord.Embed:
    return discord.Embed(
        title="📜 Regras do Servidor",
        description=(
            config["texto_regras"]
            + "\n\nClique no botão abaixo pra confirmar que leu e concorda. Assim o Drax libera seu acesso! 🐾"
        ),
        color=COR_EMBED,
    )


async def atualizar_ou_criar_painel(canal: Optional[discord.TextChannel], view: discord.ui.View, embed: discord.Embed):
    """Se já existir um painel com esse título no canal, edita a mensagem. Senão, posta uma nova."""
    if canal is None:
        print("⚠️ Canal não encontrado. Confira o ID configurado (/ver-configuracao) e o acesso do Drax a ele.")
        return
    try:
        async for msg in canal.history(limit=50):
            if msg.author == bot.user and msg.embeds and msg.embeds[0].title == embed.title:
                await msg.edit(embed=embed, view=view)
                print(f"🔄 Painel '{embed.title}' atualizado em #{canal.name}.")
                return
    except discord.Forbidden:
        print(f"⚠️ Sem permissão pra ler o histórico de #{canal.name}. Dê 'Ver Histórico de Mensagens' ao Drax.")
        return
    await canal.send(embed=embed, view=view)
    print(f"🐾 Painel '{embed.title}' postado em #{canal.name}.")


# ============================================================
# EVENTOS — entrada e saída de membros
# ============================================================
@bot.event
async def on_member_join(member: discord.Member):
    canal = bot.get_channel(config["canal_boas_vindas_id"])
    if canal is None:
        return

    canal_regras = bot.get_channel(config["canal_regras_id"])
    canal_registro = bot.get_channel(config["canal_registro_id"])
    regras_txt = canal_regras.mention if canal_regras else "as regras do servidor"
    registro_txt = canal_registro.mention if canal_registro else "o canal de registro"

    embed = discord.Embed(
        title="🐕🐕🐕 Au au! Chegou gente nova!",
        description=(
            f"Bem-vindo(a), {member.mention}! Eu sou o **Drax**, o Cérbero fofinho "
            f"que toma conta desse servidor (prometo que só mordo em brincadeira 🦴).\n\n"
            f"📜 Dá uma olhada nas regras em {regras_txt}\n"
            f"📝 Depois passa lá em {registro_txt} pra pegar seus cargos!"
        ),
        color=COR_EMBED,
    )
    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Agora somos {member.guild.member_count} nessa matilha! 🐾")

    await canal.send(embed=embed)


@bot.event
async def on_member_remove(member: discord.Member):
    canal = bot.get_channel(config["canal_saidas_id"])
    if canal is None:
        return

    embed = discord.Embed(
        title="🐾 Um amigo se foi...",
        description=f"**{member}** saiu do servidor. O Drax vai abanar o rabo triste por aqui. 🐕💭",
        color=COR_EMBED,
    )
    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)

    await canal.send(embed=embed)


# ============================================================
# EVENTOS — reação no painel de registro (dá/tira cargo, estilo Carl)
# ============================================================
def _achar_cargo_pelo_emoji(emoji_str: str) -> Optional[str]:
    for _texto, dados in config["cargos_registro"].items():
        if dados["emoji"] == emoji_str:
            return dados["cargo"]
    return None


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.message_id not in config.get("mensagens_registro", []):
        return
    if payload.user_id == bot.user.id:
        return

    nome_cargo = _achar_cargo_pelo_emoji(str(payload.emoji))
    if nome_cargo is None:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    cargo = await garantir_cargo(guild, nome_cargo)
    if cargo is None:
        return

    membro = payload.member
    if membro is None:
        try:
            membro = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            return
    if membro.bot:
        return

    try:
        await membro.add_roles(cargo, reason="Drax: reagiu no painel de registro")
    except discord.Forbidden:
        print(f"⚠️ Sem permissão pra dar o cargo {cargo.name} (confira a hierarquia de cargos do Drax).")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.message_id not in config.get("mensagens_registro", []):
        return
    if payload.user_id == bot.user.id:
        return

    nome_cargo = _achar_cargo_pelo_emoji(str(payload.emoji))
    if nome_cargo is None:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    cargo = discord.utils.get(guild.roles, name=nome_cargo)
    if cargo is None:
        return

    try:
        membro = await guild.fetch_member(payload.user_id)
    except discord.NotFound:
        return
    if membro.bot:
        return

    try:
        await membro.remove_roles(cargo, reason="Drax: tirou a reação no painel de registro")
    except discord.Forbidden:
        print(f"⚠️ Sem permissão pra tirar o cargo {cargo.name} (confira a hierarquia de cargos do Drax).")


# ============================================================
# COMANDOS SLASH — configuração dinâmica (fica salva no volume)
# ============================================================
CHAVES_POR_TIPO = {
    "Boas-vindas": "canal_boas_vindas_id",
    "Saídas": "canal_saidas_id",
    "Regras": "canal_regras_id",
    "Registro": "canal_registro_id",
}


@bot.tree.command(name="configurar-canal", description="Define qual canal o Drax usa para cada função (fica salvo)")
@app_commands.describe(tipo="Qual função configurar", canal="O canal a ser usado")
@app_commands.choices(tipo=[app_commands.Choice(name=nome, value=chave) for nome, chave in CHAVES_POR_TIPO.items()])
@app_commands.checks.has_permissions(manage_guild=True)
async def configurar_canal(interaction: discord.Interaction, tipo: app_commands.Choice[str], canal: discord.TextChannel):
    config[tipo.value] = canal.id
    salvar_config()

    await interaction.response.send_message(
        f"✅ Canal de **{tipo.name}** configurado para {canal.mention}! Isso já ficou salvo — "
        f"mesmo reiniciando o bot (ou fazendo redeploy no Railway), continua assim. 💾",
        ephemeral=True,
    )

    if tipo.value == "canal_regras_id":
        await atualizar_ou_criar_painel(canal, PainelRegras(), montar_embed_regras())
    elif tipo.value == "canal_registro_id":
        await sincronizar_paineis_registro(canal)


@bot.tree.command(
    name="adicionar-cargo-registro",
    description="Adiciona (ou atualiza) uma reação de cargo no painel de registro",
)
@app_commands.describe(
    nome="Nome de exibição na lista (ex: Gamer)",
    cargo="Cargo do servidor que será dado/removido ao reagir",
    emoji="Emoji usado para reagir (ex: 🎮 ou 🔴)",
    grupo="Categoria do painel (ex: Cores, Verificação, Pings). Cada categoria vira sua própria mensagem",
)
@app_commands.checks.has_permissions(manage_roles=True)
async def adicionar_cargo_registro(
    interaction: discord.Interaction,
    nome: str,
    cargo: discord.Role,
    emoji: str,
    grupo: str = "Geral",
):
    for outro_nome, dados in config["cargos_registro"].items():
        if dados["emoji"] == emoji and outro_nome != nome:
            await interaction.response.send_message(
                f"🐾 O emoji {emoji} já tá sendo usado pelo cargo **{outro_nome}** (grupo **{dados.get('grupo', 'Geral')}**)! "
                f"Escolhe outro emoji.",
                ephemeral=True,
            )
            return

    await interaction.response.defer(ephemeral=True, thinking=True)

    config["cargos_registro"][nome] = {"cargo": cargo.name, "emoji": emoji, "grupo": grupo}
    salvar_config()

    canal_registro = bot.get_channel(config["canal_registro_id"])
    await sincronizar_paineis_registro(canal_registro)

    await interaction.followup.send(
        f"✅ **{nome}** ({emoji}) ligado ao cargo **{cargo.name}** no grupo **{grupo}** salvo! "
        f"O painel de registro já foi atualizado — reage lá pra testar. 🐾",
        ephemeral=True,
    )



@bot.tree.command(name="remover-cargo-registro", description="Remove uma reação de cargo do painel de registro")
@app_commands.describe(nome="Nome exato cadastrado (igual aparece em /ver-configuracao)")
@app_commands.checks.has_permissions(manage_roles=True)
async def remover_cargo_registro(interaction: discord.Interaction, nome: str):
    if nome not in config["cargos_registro"]:
        await interaction.response.send_message(
            f"🐾 Não achei nenhum cargo chamado **{nome}** no painel. Use /ver-configuracao pra ver os atuais.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    del config["cargos_registro"][nome]
    salvar_config()

    canal_registro = bot.get_channel(config["canal_registro_id"])
    await sincronizar_paineis_registro(canal_registro)

    await interaction.followup.send(f"🗑️ **{nome}** removido do painel e já salvo!", ephemeral=True)


@bot.tree.command(name="definir-cargo-verificado", description="Define qual cargo é dado a quem aceita as regras")
@app_commands.describe(cargo="Cargo dado a quem concorda com as regras")
@app_commands.checks.has_permissions(manage_roles=True)
async def definir_cargo_verificado(interaction: discord.Interaction, cargo: discord.Role):
    config["cargo_verificado"] = cargo.name
    salvar_config()
    await interaction.response.send_message(
        f"✅ Cargo de verificação definido como **{cargo.name}** e salvo!", ephemeral=True
    )


@bot.tree.command(name="ver-configuracao", description="Mostra a configuração atual do Drax (canais e cargos salvos)")
@app_commands.checks.has_permissions(manage_guild=True)
async def ver_configuracao(interaction: discord.Interaction):
    def fmt_canal(chave: str) -> str:
        canal = bot.get_channel(config[chave])
        return canal.mention if canal else f"⚠️ não encontrado (ID {config[chave]})"

    embed = discord.Embed(title="⚙️ Configuração atual do Drax", color=COR_EMBED)
    embed.add_field(name="Boas-vindas", value=fmt_canal("canal_boas_vindas_id"), inline=True)
    embed.add_field(name="Saídas", value=fmt_canal("canal_saidas_id"), inline=True)
    embed.add_field(name="Regras", value=fmt_canal("canal_regras_id"), inline=True)
    embed.add_field(name="Registro", value=fmt_canal("canal_registro_id"), inline=True)
    embed.add_field(name="Cargo de verificado", value=f"`{config['cargo_verificado']}`", inline=True)

    grupos = agrupar_cargos(list(config["cargos_registro"].items()))
    if not grupos:
        embed.add_field(name="Cargos do painel de registro", value="_nenhum cargo configurado_", inline=False)
    else:
        for nome_grupo, itens in grupos.items():
            texto = "\n".join(f"• **{texto}** {dados['emoji']} → `{dados['cargo']}`" for texto, dados in itens)
            embed.add_field(name=f"📋 {nome_grupo}", value=texto, inline=False)

    embed.set_footer(text=f"Arquivo salvo em: {ARQUIVO_CONFIG}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------- comandos manuais pra forçar um post novo (opcional) ----------
@bot.tree.command(name="painel-registro", description="Força um novo post do painel de registro no canal atual")
@app_commands.checks.has_permissions(manage_roles=True)
async def painel_registro(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    await sincronizar_paineis_registro(interaction.channel, recriar=True)
    await interaction.followup.send("🐾 Painel de registro reenviado nesse canal!", ephemeral=True)


@bot.tree.command(name="painel-regras", description="Força um novo post do painel de regras no canal atual")
@app_commands.checks.has_permissions(manage_roles=True)
async def painel_regras(interaction: discord.Interaction):
    await interaction.response.send_message(embed=montar_embed_regras(), view=PainelRegras())


@bot.tree.command(
    name="criar-cargos",
    description="Cria (se estiverem faltando) todos os cargos do painel de registro e o cargo de verificado",
)
@app_commands.checks.has_permissions(manage_roles=True)
async def criar_cargos(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    criados = await garantir_todos_cargos_registro(interaction.guild)

    existia_verificado = discord.utils.get(interaction.guild.roles, name=config["cargo_verificado"]) is not None
    cargo_verificado = await garantir_cargo(interaction.guild, config["cargo_verificado"])
    if cargo_verificado and not existia_verificado:
        criados.append(cargo_verificado.name)

    if criados:
        lista = "\n".join(f"• `{nome}`" for nome in criados)
        texto = f"🐾 Criei os cargos que ainda faltavam:\n{lista}"
    else:
        texto = "🐾 Todos os cargos já existiam, nenhum precisou ser criado."

    canal_registro = bot.get_channel(config["canal_registro_id"])
    await sincronizar_paineis_registro(canal_registro)

    await interaction.followup.send(texto, ephemeral=True)


async def _erro_permissao(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "🐾 Você não tem permissão suficiente pra usar esse comando!", ephemeral=True
        )
    else:
        raise error


for _cmd in (
    configurar_canal,
    adicionar_cargo_registro,
    remover_cargo_registro,
    definir_cargo_verificado,
    ver_configuracao,
    painel_registro,
    painel_regras,
    criar_cargos,
):
    _cmd.error(_erro_permissao)


# ============================================================
# ATUALIZAÇÃO AUTOMÁTICA PERIÓDICA (sem precisar reiniciar o bot)
# ============================================================
@tasks.loop(minutes=1)
async def atualizar_paineis_automaticamente():
    """Roda sozinha a cada 1 minuto, o tempo todo enquanto o bot tiver de pé
    (não precisa reiniciar/redeploy no Railway pra ver os painéis corrigidos):
    recria cargo que sumiu, corrige cor errada e atualiza o embed."""
    canal_regras = bot.get_channel(config["canal_regras_id"])
    if canal_regras is not None:
        await garantir_cargo(canal_regras.guild, config["cargo_verificado"])
        await atualizar_ou_criar_painel(canal_regras, PainelRegras(), montar_embed_regras())

    await sincronizar_paineis_registro(bot.get_channel(config["canal_registro_id"]))


@atualizar_paineis_automaticamente.before_loop
async def antes_de_atualizar_paineis_automaticamente():
    await bot.wait_until_ready()


# ============================================================
# INICIALIZAÇÃO
# ============================================================
@bot.event
async def on_ready():
    # Reregistra a view persistente do painel de regras (pro botão funcionar mesmo após reiniciar o bot)
    # O painel de registro não precisa disso: reações funcionam sem view/interação registrada.
    bot.add_view(PainelRegras())

    try:
        sincronizados = await bot.tree.sync()
        print(f"🐾 {len(sincronizados)} comando(s) slash sincronizado(s).")
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar comandos: {e}")

    # Garante que os cargos já existam ANTES de postar os painéis (senão o botão
    # e as reações não têm o que dar pra quem clicar/reagir)
    canal_regras = bot.get_channel(config["canal_regras_id"])
    if canal_regras is not None:
        await garantir_cargo(canal_regras.guild, config["cargo_verificado"])

    # Posta/atualiza os painéis automaticamente nos canais configurados
    await atualizar_ou_criar_painel(canal_regras, PainelRegras(), montar_embed_regras())
    await sincronizar_paineis_registro(bot.get_channel(config["canal_registro_id"]))

    # A partir daqui, os painéis se resincronizam sozinhos a cada 1 minuto
    if not atualizar_paineis_automaticamente.is_running():
        atualizar_paineis_automaticamente.start()

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="os 3 portões 🐾")
    )
    print(f"🐕🐕🐕 Drax tá online como {bot.user}! Au au!")
    print(f"💾 Configuração persistente em: {ARQUIVO_CONFIG.resolve()}")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "Token não encontrado! Crie um arquivo .env na mesma pasta com:\nDISCORD_TOKEN=seu_token_aqui"
        )
    bot.run(TOKEN)
