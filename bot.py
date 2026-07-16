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
COMANDOS (precisam de permissão de administração no servidor)
--------------------------------------------------------------------------
/configurar-canal tipo:<Boas-vindas|Saídas|Regras|Registro> canal:#canal
    -> Define qual canal o Drax usa pra cada função. Fica salvo, e se for o
       canal de Regras ou Registro, o painel já é postado/atualizado ali na hora.

/adicionar-cargo-registro nome:"Gamer" cargo:@Gamer emoji:🎮
    -> Adiciona (ou atualiza) uma linha no painel de registro. Quem reagir com
       esse emoji na mensagem recebe o cargo automaticamente (e perde o cargo
       se tirar a reação depois). O painel já existente é atualizado na hora.

/remover-cargo-registro nome:"Gamer"
    -> Remove uma linha/reação do painel de registro (atualiza na hora também).

/definir-cargo-verificado cargo:@Verificado
    -> Define qual cargo é dado a quem clica em "concordo com as regras".

/ver-configuracao
    -> Mostra a configuração atual (canais e cargos salvos).

/painel-registro e /painel-regras
    -> Forçam um novo post manual dos painéis no canal atual (opcional).

--------------------------------------------------------------------------
PAINEL DE REGISTRO (estilo Carl — reaction roles)
--------------------------------------------------------------------------
O painel de registro não usa mais botões: funciona igual ao reaction-role
clássico do Carl-bot. O Drax posta um embed listando emoji + cargo, e as
reações aparecem embaixo da mensagem (nativas do Discord). Quem reage ganha
o cargo, quem tira a reação perde o cargo. Como o Discord só permite 20
reações diferentes por mensagem, se você cadastrar mais de 20 cargos o Drax
divide automaticamente em várias mensagens seguidas (parte 1, parte 2...),
do mesmo jeito que o Carl faz.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands
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
        "Gamer": {"cargo": "Gamer", "emoji": "🎮"},
        "Artista": {"cargo": "Artista", "emoji": "🎨"},
        "Música": {"cargo": "Música", "emoji": "🎵"},
        "Anime": {"cargo": "Anime", "emoji": "🍥"},
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


def dividir_em_blocos(cargos: list, tamanho: int = MAX_REACOES_POR_MENSAGEM) -> list:
    """Quebra a lista de cargos em blocos de até `tamanho` itens (1 bloco = 1 mensagem)."""
    return [cargos[i:i + tamanho] for i in range(0, len(cargos), tamanho)] or [[]]


def montar_embed_registro(guild: Optional[discord.Guild], bloco: list, indice: int, total: int) -> discord.Embed:
    linhas = []
    for _texto, dados in bloco:
        cargo_obj = discord.utils.get(guild.roles, name=dados["cargo"]) if guild else None
        cargo_txt = cargo_obj.mention if cargo_obj else f"@{dados['cargo']}"
        linhas.append(f"{dados['emoji']}  {cargo_txt}")

    titulo = "🐕🐕🐕 Registro do Drax" + (f" (parte {indice + 1})" if total > 1 else "")
    intro = (
        "Oi! Eu sou o **Drax**, seu Cérbero fofo de três cabeças guardando esse servidor!\n\n"
        "Reaja com o emoji correspondente pra pegar o cargo. Tire a reação pra perder o cargo. Au au! 🐾\n\n"
        if indice == 0 else ""
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
    """Cria ou atualiza as mensagens do painel de registro (1 mensagem por bloco de até 20 cargos)."""
    if canal is None:
        print("⚠️ Canal de registro não encontrado. Confira o ID configurado (/ver-configuracao) e o acesso do Drax a ele.")
        return

    blocos = dividir_em_blocos(list(config["cargos_registro"].items()))
    ids_atuais = [] if recriar else list(config.get("mensagens_registro", []))
    novas_ids = []

    for indice, bloco in enumerate(blocos):
        embed = montar_embed_registro(canal.guild, bloco, indice, len(blocos))

        if indice < len(ids_atuais):
            try:
                msg = await canal.fetch_message(ids_atuais[indice])
                await msg.edit(embed=embed)
                await sincronizar_reacoes(msg, bloco)
                novas_ids.append(msg.id)
                continue
            except discord.NotFound:
                pass

        msg = await canal.send(embed=embed)
        await sincronizar_reacoes(msg, bloco)
        novas_ids.append(msg.id)

    # apaga mensagens antigas que sobraram (ex: cargos foram removidos e agora precisa de menos partes)
    for id_sobrando in ids_atuais[len(blocos):]:
        try:
            msg_antiga = await canal.fetch_message(id_sobrando)
            await msg_antiga.delete()
        except discord.NotFound:
            pass

    config["mensagens_registro"] = novas_ids
    salvar_config()
    print(f"🐾 Painel de registro sincronizado em #{canal.name} ({len(novas_ids)} mensagem(ns)).")


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
        cargo = discord.utils.get(interaction.guild.roles, name=config["cargo_verificado"])
        if cargo is None:
            await interaction.response.send_message(
                f"🐾 Não achei o cargo **{config['cargo_verificado']}**. "
                f"Peça pra um admin criar um cargo com esse nome exato.",
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
    cargo = discord.utils.get(guild.roles, name=nome_cargo)
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
)
@app_commands.checks.has_permissions(manage_roles=True)
async def adicionar_cargo_registro(
    interaction: discord.Interaction,
    nome: str,
    cargo: discord.Role,
    emoji: str,
):
    for outro_nome, dados in config["cargos_registro"].items():
        if dados["emoji"] == emoji and outro_nome != nome:
            await interaction.response.send_message(
                f"🐾 O emoji {emoji} já tá sendo usado pelo cargo **{outro_nome}**! Escolhe outro emoji.",
                ephemeral=True,
            )
            return

    await interaction.response.defer(ephemeral=True, thinking=True)

    config["cargos_registro"][nome] = {"cargo": cargo.name, "emoji": emoji}
    salvar_config()

    canal_registro = bot.get_channel(config["canal_registro_id"])
    await sincronizar_paineis_registro(canal_registro)

    await interaction.followup.send(
        f"✅ **{nome}** ({emoji}) ligado ao cargo **{cargo.name}** salvo! "
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

    cargos_txt = (
        "\n".join(
            f"• **{texto}** → cargo `{dados['cargo']}` {dados.get('emoji') or ''}"
            for texto, dados in config["cargos_registro"].items()
        )
        or "_nenhum cargo configurado_"
    )

    embed = discord.Embed(title="⚙️ Configuração atual do Drax", color=COR_EMBED)
    embed.add_field(name="Boas-vindas", value=fmt_canal("canal_boas_vindas_id"), inline=True)
    embed.add_field(name="Saídas", value=fmt_canal("canal_saidas_id"), inline=True)
    embed.add_field(name="Regras", value=fmt_canal("canal_regras_id"), inline=True)
    embed.add_field(name="Registro", value=fmt_canal("canal_registro_id"), inline=True)
    embed.add_field(name="Cargo de verificado", value=f"`{config['cargo_verificado']}`", inline=True)
    embed.add_field(name="Cargos do painel de registro", value=cargos_txt, inline=False)
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
):
    _cmd.error(_erro_permissao)


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

    # Posta/atualiza os painéis automaticamente nos canais configurados
    await atualizar_ou_criar_painel(bot.get_channel(config["canal_regras_id"]), PainelRegras(), montar_embed_regras())
    await sincronizar_paineis_registro(bot.get_channel(config["canal_registro_id"]))

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
