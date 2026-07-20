"""
🐕🐕🐕 Drax — Bot Cérbero fofo para Discord (arquivo único, com configuração persistente)

Requisitos:
    pip install discord.py python-dotenv PyNaCl

    (o PyNaCl é necessário pro Drax conseguir ENTRAR em call — ele faz isso pra
    conseguir detectar efeitos de voz usados. Sem o PyNaCl instalado, os logs de
    entrada/saída/troca de call continuam funcionando normalmente, só o log de
    "usou efeito" que não funciona.)

Configuração (.env na mesma pasta):
    DISCORD_TOKEN=seu_token_aqui

Uso:
    python drax.py

--------------------------------------------------------------------------
LOGS (canais fixos, não precisa configurar nada)
--------------------------------------------------------------------------
Dois canais de log ficam com o ID fixo no código (procure por CANAL_LOGS_CHAT_ID
e CANAL_LOGS_CALL_ID mais abaixo se precisar trocar):

📋 Logs de chat (1528866964171260005)
    - Mensagem apagada: mostra autor, canal, conteúdo antes de sumir, anexos, e
      quem apagou (o próprio autor OU um moderador — descoberto pelo Registro de
      Auditoria; se apagou o próprio, aparece "o próprio autor").
    - Mensagem editada: mostra antes/depois do texto e link direto pra mensagem.
    - Apagão em massa (bulk delete): mostra quantas mensagens e quem eram os
      autores (só das que estavam em cache).
    - Precisa da permissão "Ver Registro de Auditoria" pro Drax pra conseguir
      identificar QUEM apagou a mensagem de outra pessoa (sem essa permissão,
      ele ainda loga a mensagem apagada, só não sabe dizer quem apagou).

🔊 Logs de call (1528867083000217754)
    - Entrou / saiu / trocou de call.
    - Foi puxado(a) (movido) pra outra call: mostra quem moveu (via Registro de
      Auditoria — precisa da permissão "Ver Registro de Auditoria").
    - Foi desconectado(a) da call: mostra quem desconectou, também via Registro
      de Auditoria.
    - Usou efeito de voz (reação animada ou som do soundboard): AVISO — o
      Discord só manda esse evento pro bot na call em que ELE MESMO estiver
      conectado (não dá pra "ouvir" todas as calls de fora). Por isso o Drax
      entra sozinho, mudo e surdo, na call que tiver mais gente no momento, e
      pula pra outra call se ela ficar vazia e outra tiver mais gente. Se tiver
      mais de uma call ativa ao mesmo tempo, só a que ele estiver dentro tem os
      efeitos registrados — é uma limitação da própria API do Discord.

--------------------------------------------------------------------------
ATUALIZAÇÃO AUTOMÁTICA (a cada 1 minuto, sem precisar reiniciar)
--------------------------------------------------------------------------
Enquanto o bot estiver rodando (no Railway ou local), ele resincroniza os
painéis sozinho a cada 1 minuto: recria qualquer cargo que tenha sumido,
corrige cor de cargo desatualizada e atualiza o texto do embed. Não precisa
reiniciar/redeploy pra ver isso acontecer — só precisa o processo estar de pé.

--------------------------------------------------------------------------
ARMAZENAMENTO PERSISTENTE (Railway Volume) — PASSO A PASSO
--------------------------------------------------------------------------
Sem um Volume, o Railway apaga o sistema de arquivos do serviço a cada novo
deploy/restart — ou seja, TODA a configuração (canais, cargos do painel, IDs
das mensagens) some e volta pro padrão de fábrica. É bem provável que seja
essa a causa de reações que "somem" ou cargos que parecem não aplicar: depois
de um restart sem volume, o Drax perde o rastro das mensagens antigas do
painel, posta um painel NOVO, e qualquer reação feita no painel antigo (que
ainda está lá, visível, mas "morto") não faz mais nada.

Como resolver, direto no site do Railway:
    1. Abra o projeto no Railway e clique no serviço do bot (o card do Drax).
    2. Vá na aba "Settings" desse serviço.
    3. Role até a seção "Volumes" e clique em "+ New Volume" (ou "Add Volume").
    4. No campo de "Mount Path", digite: /data
       (pode ser outro caminho, mas /data é o mais comum; não precisa criar a
       pasta antes, o Railway cuida disso)
    5. Salve/confirme. O Railway reinicia o serviço sozinho e já cria a
       variável de ambiente RAILWAY_VOLUME_MOUNT_PATH automaticamente
       apontando pra esse caminho — não precisa configurar essa variável
       na mão, o Drax já lê ela sozinho (ver DATA_DIR logo abaixo).
    6. Depois que o serviço reiniciar com o volume anexado, confira nos
       "Logs" se a linha de aviso "RAILWAY_VOLUME_MOUNT_PATH não detectado"
       (que aparece no início deste arquivo) SUMIU. Se sumiu, tá persistente.
    7. Só então: apague manualmente do canal de registro os painéis
       duplicados/antigos que sobraram dos restarts anteriores (o bot não
       sabe que eles existem, então não apaga sozinho), e rode
       /painel-registro (ou /criar-cargos) uma vez pra postar a versão
       definitiva, que agora vai ficar salva de verdade.

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

/diagnostico-cargos
    -> Mostra, cargo por cargo, se ele existe no servidor e se o Drax tem
       permissão + hierarquia suficiente pra gerenciar ele. Use esse comando
       se as reações/botão não estiverem dando o cargo — ele aponta certinho
       se falta permissão "Gerenciar Cargos" ou se o cargo do Drax precisa
       subir na hierarquia.

/diagnostico-armazenamento
    -> Mostra se o Volume do Railway está mesmo detectado e a config
       persistindo (sem precisar entrar no site do Railway pra ver os Logs).
       Use esse comando se os painéis ficarem duplicando a cada restart.

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
from datetime import datetime
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

if not os.getenv("RAILWAY_VOLUME_MOUNT_PATH"):
    print(
        "⚠️⚠️⚠️ ATENÇÃO: RAILWAY_VOLUME_MOUNT_PATH não detectado — a configuração "
        "(canais, cargos do painel, IDs das mensagens) NÃO está persistente agora. "
        "Qualquer redeploy/restart no Railway apaga esse progresso e o bot posta os "
        "painéis de novo do zero, deixando as mensagens antigas órfãs no canal (e "
        "reações feitas nelas param de funcionar). Anexa um Volume ao serviço em "
        "Settings > Volumes pra resolver isso — passo a passo no topo deste arquivo."
    )

# Cor lateral dos embeds (tema "fogo do submundo")
COR_EMBED = 0xFF6A00

# Canais de log (fixos — não vêm do config.json de propósito, pra não sumir/mudar
# sem querer). Se precisar trocar, é só editar os números aqui.
CANAL_LOGS_CHAT_ID = 1528866964171260005
CANAL_LOGS_CALL_ID = 1528867083000217754

logging.basicConfig(level=logging.INFO)

# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.members = True          # necessário para on_member_join / on_member_remove
intents.message_content = True  # necessário pra logar o conteúdo de mensagens editadas/apagadas
intents.voice_states = True     # necessário pros logs de call (entrar/sair/trocar/efeitos)

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


# ============================================================
# LOGS DE CHAT — mensagens apagadas e editadas
# ============================================================
LIMITE_TEXTO_LOG = 1000  # margem de segurança (limite real de um campo de embed é 1024)


def _cortar_para_log(texto: Optional[str], limite: int = LIMITE_TEXTO_LOG) -> str:
    if not texto:
        return "*(sem texto — deve ser só imagem/anexo/embed/sticker)*"
    texto = texto.strip()
    if len(texto) > limite:
        return texto[:limite] + "…"
    return texto


async def _quem_apagou_mensagem(guild: Optional[discord.Guild], autor_id: int, canal_id: int) -> str:
    """Descobre quem apagou a mensagem, olhando o Registro de Auditoria: apagar a
    PRÓPRIA mensagem não gera entrada nenhuma lá, então se não achar nada recente
    pra esse autor é porque foi ele mesmo quem apagou."""
    if guild is None:
        return "❓ desconhecido"
    if guild.me is None or not guild.me.guild_permissions.view_audit_log:
        return "❓ não sei dizer (falta a permissão 'Ver Registro de Auditoria' pro Drax)"

    agora = discord.utils.utcnow()
    try:
        async for entrada in guild.audit_logs(limit=10, action=discord.AuditLogAction.message_delete):
            if (agora - entrada.created_at).total_seconds() > 10:
                break  # o audit log vem do mais recente pro mais antigo
            if entrada.target and entrada.target.id == autor_id:
                canal_extra = getattr(entrada.extra, "channel", None)
                if canal_extra is None or canal_extra.id == canal_id:
                    return f"{entrada.user.mention} (moderação)" if entrada.user else "um moderador"
    except discord.Forbidden:
        return "❓ não sei dizer (falta a permissão 'Ver Registro de Auditoria' pro Drax)"

    return "o próprio autor"


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    if payload.guild_id is None:
        return
    canal_logs = bot.get_channel(CANAL_LOGS_CHAT_ID)
    if canal_logs is None:
        return

    msg = payload.cached_message
    if msg is not None and msg.author.bot:
        return

    canal_original = bot.get_channel(payload.channel_id)
    canal_txt = canal_original.mention if canal_original else f"`#{payload.channel_id}`"

    embed = discord.Embed(title="🗑️ Mensagem apagada", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Canal", value=canal_txt, inline=True)

    if msg is not None:
        guild = bot.get_guild(payload.guild_id)
        apagado_por = await _quem_apagou_mensagem(guild, msg.author.id, payload.channel_id)

        embed.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
        embed.add_field(name="Autor", value=msg.author.mention, inline=True)
        embed.add_field(name="Apagado por", value=apagado_por, inline=True)
        embed.add_field(name="Conteúdo", value=_cortar_para_log(msg.content), inline=False)
        if msg.attachments:
            anexos = "\n".join(f"📎 {a.filename}" for a in msg.attachments)
            embed.add_field(name="Anexos", value=_cortar_para_log(anexos, 500), inline=False)
        embed.set_footer(text=f"ID da mensagem: {payload.message_id} • ID do autor: {msg.author.id}")
    else:
        embed.add_field(
            name="Conteúdo",
            value="*(não sei dizer — a mensagem não estava em cache; provavelmente era antiga ou o bot reiniciou depois que ela foi enviada)*",
            inline=False,
        )
        embed.set_footer(text=f"ID da mensagem: {payload.message_id}")

    await canal_logs.send(embed=embed)


@bot.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    if payload.guild_id is None:
        return
    canal_logs = bot.get_channel(CANAL_LOGS_CHAT_ID)
    if canal_logs is None:
        return

    canal_original = bot.get_channel(payload.channel_id)
    canal_txt = canal_original.mention if canal_original else f"`#{payload.channel_id}`"

    embed = discord.Embed(
        title="🧹 Mensagens apagadas em massa",
        description=f"**{len(payload.message_ids)}** mensagens apagadas de uma vez em {canal_txt}.",
        color=discord.Color.dark_red(),
        timestamp=discord.utils.utcnow(),
    )

    mensagens_em_cache = [m for m in payload.cached_messages if not m.author.bot]
    if mensagens_em_cache:
        contagem: dict = {}
        for m in mensagens_em_cache:
            contagem[str(m.author)] = contagem.get(str(m.author), 0) + 1
        resumo = "\n".join(f"• {autor}: {qtd}" for autor, qtd in contagem.items())
        embed.add_field(
            name=f"Autores (de {len(mensagens_em_cache)} mensagens que estavam em cache)",
            value=_cortar_para_log(resumo, 800),
            inline=False,
        )

    await canal_logs.send(embed=embed)


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    if payload.guild_id is None:
        return

    novo_conteudo = payload.data.get("content")
    if novo_conteudo is None:
        return  # edição de outra coisa (embed de link, etc.), não do texto em si

    antes = payload.cached_message
    if antes is not None:
        if antes.author.bot:
            return
        if antes.content == novo_conteudo:
            return  # sem mudança real de texto

    canal_original = bot.get_channel(payload.channel_id)
    if canal_original is None:
        return

    autor = antes.author if antes is not None else None
    if autor is None:
        try:
            msg_atual = await canal_original.fetch_message(payload.message_id)
            autor = msg_atual.author
        except (discord.NotFound, discord.Forbidden):
            autor = None
    if autor is not None and autor.bot:
        return

    canal_logs = bot.get_channel(CANAL_LOGS_CHAT_ID)
    if canal_logs is None:
        return

    link = f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"

    embed = discord.Embed(title="📝 Mensagem editada", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Canal", value=canal_original.mention, inline=True)
    if autor is not None:
        embed.set_author(name=str(autor), icon_url=autor.display_avatar.url)
        embed.add_field(name="Autor", value=autor.mention, inline=True)
    embed.add_field(
        name="Antes",
        value=_cortar_para_log(antes.content) if antes is not None else "*(não sei — mensagem não estava em cache)*",
        inline=False,
    )
    embed.add_field(name="Depois", value=_cortar_para_log(novo_conteudo), inline=False)
    embed.add_field(name="Link", value=f"[Ir para a mensagem]({link})", inline=False)
    embed.set_footer(text=f"ID da mensagem: {payload.message_id}")

    await canal_logs.send(embed=embed)


async def sincronizar_paineis_registro(canal: Optional[discord.TextChannel], recriar: bool = False):
    """Cria ou atualiza as mensagens do painel de registro: uma (ou mais, se passar de
    20 cargos) mensagem por grupo — Cores, Verificação, Pings etc.

    Além dos IDs salvos em config, o Drax também varre o histórico do canal procurando
    mensagens dele mesmo cujo embed já tenha o título esperado (ex: "🐕🐕🐕 Pings"). Isso
    garante que NUNCA cria mensagens novas se já existir uma pro mesmo grupo — mesmo que
    o arquivo de configuração seja perdido (ex: reinício/redeploy sem volume persistente
    no Railway) — e ainda apaga qualquer duplicata que tenha sobrado de reinícios antigos."""
    if canal is None:
        print("⚠️ Canal de registro não encontrado. Confira o ID configurado (/ver-configuracao) e o acesso do Drax a ele.")
        return

    await garantir_todos_cargos_registro(canal.guild)

    grupos = agrupar_cargos(list(config["cargos_registro"].items()))

    blocos_por_grupo = {}
    titulos_esperados = set()
    for nome_grupo, itens in grupos.items():
        blocos = dividir_em_blocos(itens)
        blocos_por_grupo[nome_grupo] = blocos
        total = len(blocos)
        for indice in range(total):
            titulo = f"🐕🐕🐕 {nome_grupo}" + (f" (parte {indice + 1})" if total > 1 else "")
            titulos_esperados.add(titulo)

    mensagens_por_titulo: dict = {}

    if not recriar:
        # 1) caminho rápido: tenta pelos IDs salvos em config
        for msg_id in config.get("mensagens_registro", []):
            try:
                msg = await canal.fetch_message(msg_id)
                if msg.embeds and msg.embeds[0].title in titulos_esperados:
                    mensagens_por_titulo.setdefault(msg.embeds[0].title, msg)
            except discord.NotFound:
                continue

        # 2) rede de segurança: varre o histórico por título. Cobre tanto o caso de IDs
        # perdidos (config resetado) quanto duplicatas deixadas por reinícios anteriores
        # (essas duplicatas extras são apagadas na hora).
        try:
            async for msg in canal.history(limit=200):
                if msg.author != bot.user or not msg.embeds:
                    continue
                titulo_msg = msg.embeds[0].title
                if titulo_msg not in titulos_esperados:
                    continue
                if titulo_msg in mensagens_por_titulo:
                    if mensagens_por_titulo[titulo_msg].id != msg.id:
                        try:
                            await msg.delete()
                        except discord.NotFound:
                            pass
                else:
                    mensagens_por_titulo[titulo_msg] = msg
        except discord.Forbidden:
            print(f"⚠️ Sem permissão pra ler o histórico de #{canal.name}. Dê 'Ver Histórico de Mensagens' ao Drax.")

    novas_ids = []
    primeiro_bloco_geral = True

    for nome_grupo, blocos in blocos_por_grupo.items():
        total = len(blocos)
        for indice, bloco in enumerate(blocos):
            embed = montar_embed_registro(canal.guild, nome_grupo, bloco, indice, total, primeiro_bloco_geral)
            primeiro_bloco_geral = False
            titulo = embed.title

            msg_existente = mensagens_por_titulo.pop(titulo, None)
            if msg_existente is not None:
                try:
                    await msg_existente.edit(embed=embed)
                    await sincronizar_reacoes(msg_existente, bloco)
                    novas_ids.append(msg_existente.id)
                    continue
                except discord.NotFound:
                    pass

            msg = await canal.send(embed=embed)
            await sincronizar_reacoes(msg, bloco)
            novas_ids.append(msg.id)

    # apaga mensagens de grupos que não existem mais (ex: um cargo removido esvaziou o grupo)
    for msg_sobrando in mensagens_por_titulo.values():
        try:
            await msg_sobrando.delete()
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
# LOGS DE CALL — entrou/saiu/trocou/puxão/efeito de voz
# ============================================================
JANELA_AUDIT_LOG_SEGUNDOS = 8  # quão "recente" uma entrada do audit log precisa ser pra contar


async def _quem_moveu_para(guild: discord.Guild, canal_destino_id: int):
    """Procura no Registro de Auditoria quem usou 'mover membro' pra esse canal
    recentemente. O Discord não guarda QUAL membro específico foi movido quando
    são vários de uma vez (só o total), então em caso de mais de 1 pessoa movida
    junto isso é reportado, mas sem certeza absoluta de qual delas é o alvo."""
    if guild.me is None or not guild.me.guild_permissions.view_audit_log:
        return None
    agora = discord.utils.utcnow()
    try:
        async for entrada in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_move):
            if (agora - entrada.created_at).total_seconds() > JANELA_AUDIT_LOG_SEGUNDOS:
                break
            canal_extra = getattr(entrada.extra, "channel", None)
            if canal_extra is not None and canal_extra.id == canal_destino_id:
                return entrada
    except discord.Forbidden:
        return None
    return None


async def _quem_desconectou(guild: discord.Guild):
    """Mesma ideia, mas pra quem foi desconectado da call inteira (não só movido
    de canal). O audit log de 'Disconnect' também não amarra num membro específico."""
    if guild.me is None or not guild.me.guild_permissions.view_audit_log:
        return None
    agora = discord.utils.utcnow()
    try:
        async for entrada in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_disconnect):
            if (agora - entrada.created_at).total_seconds() > JANELA_AUDIT_LOG_SEGUNDOS:
                break
            return entrada
    except discord.Forbidden:
        return None
    return None


async def _gerenciar_presenca_para_efeitos(guild: discord.Guild):
    """O Discord só manda o evento de 'efeito de voz' (reação animada / som do
    soundboard) pro bot que estiver DENTRO da call — não dá pra detectar de fora.
    Por isso o Drax entra sozinho (mudo e surdo) na call com mais gente agora, e
    sai/pula de canal conforme as calls esvaziam ou enchem.

    LIMITAÇÃO: um bot só fica em 1 call por servidor de cada vez, então se tiver
    mais de uma call ativa ao mesmo tempo, só os efeitos usados na call em que o
    Drax está entram no log — as outras calls simultâneas ficam de fora."""
    voice_client = guild.voice_client

    melhor_canal, melhor_contagem = None, 0
    for canal in guild.voice_channels:
        humanos = sum(1 for m in canal.members if not m.bot)
        if humanos > melhor_contagem:
            melhor_canal, melhor_contagem = canal, humanos

    if melhor_canal is None:
        if voice_client is not None:
            await voice_client.disconnect(force=True)
        return

    if voice_client is None:
        try:
            await melhor_canal.connect(self_mute=True, self_deaf=True)
        except discord.ClientException as e:
            # geralmente falta instalar o PyNaCl ("pip install PyNaCl")
            print(f"⚠️ Não consegui entrar em call pra monitorar efeitos de voz: {e}")
        except discord.Forbidden:
            print(f"⚠️ Sem permissão pra entrar em #{melhor_canal.name} pra monitorar efeitos de voz.")
    elif voice_client.channel.id != melhor_canal.id:
        try:
            await voice_client.move_to(melhor_canal)
        except discord.HTTPException:
            pass


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if before.channel == after.channel:
        return  # só mudou mute/deaf/câmera/stream — não é entrada/saída/troca de call

    if not member.bot:
        canal_logs = bot.get_channel(CANAL_LOGS_CALL_ID)
        if canal_logs is not None:
            if before.channel is None and after.channel is not None:
                embed = discord.Embed(title="🔊 Entrou na call", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.add_field(name="Membro", value=member.mention, inline=True)
                embed.add_field(name="Canal", value=after.channel.mention, inline=True)
                await canal_logs.send(embed=embed)

            elif before.channel is not None and after.channel is None:
                entrada = await _quem_desconectou(member.guild)
                if entrada is not None:
                    extra = f" (desconectou {entrada.extra.count} pessoa(s) de uma vez)" if entrada.extra.count > 1 else ""
                    embed = discord.Embed(title="👢 Foi desconectado(a) da call", color=discord.Color.dark_orange(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="Por", value=f"{entrada.user.mention if entrada.user else 'desconhecido'}{extra}", inline=False)
                else:
                    embed = discord.Embed(title="🔇 Saiu da call", color=discord.Color.greyple(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.add_field(name="Membro", value=member.mention, inline=True)
                embed.add_field(name="Canal", value=before.channel.mention, inline=True)
                await canal_logs.send(embed=embed)

            else:  # trocou de canal de voz
                entrada = await _quem_moveu_para(member.guild, after.channel.id)
                if entrada is not None:
                    extra = f" (moveu {entrada.extra.count} pessoa(s) de uma vez)" if entrada.extra.count > 1 else ""
                    embed = discord.Embed(title="🫳 Foi puxado(a) para outra call", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="Por", value=f"{entrada.user.mention if entrada.user else 'desconhecido'}{extra}", inline=False)
                else:
                    embed = discord.Embed(title="🔀 Trocou de call", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.add_field(name="Membro", value=member.mention, inline=True)
                embed.add_field(name="De", value=before.channel.mention, inline=True)
                embed.add_field(name="Para", value=after.channel.mention, inline=True)
                await canal_logs.send(embed=embed)

    await _gerenciar_presenca_para_efeitos(member.guild)


@bot.event
async def on_voice_channel_effect(effect: discord.VoiceChannelEffect):
    if effect.user is None or effect.user.bot:
        return
    canal_logs = bot.get_channel(CANAL_LOGS_CALL_ID)
    if canal_logs is None:
        return

    embed = discord.Embed(title="✨ Usou um efeito na call", color=discord.Color.fuchsia(), timestamp=discord.utils.utcnow())
    embed.set_author(name=str(effect.user), icon_url=effect.user.display_avatar.url)
    embed.add_field(name="Membro", value=effect.user.mention, inline=True)
    embed.add_field(name="Canal", value=effect.channel.mention, inline=True)

    if effect.is_sound():
        volume_pct = int((effect.sound.volume or 0) * 100)
        embed.add_field(name="Tipo", value=f"🔊 Som do soundboard (ID `{effect.sound.id}`, volume {volume_pct}%)", inline=False)
    elif effect.emoji is not None:
        embed.add_field(name="Tipo", value=f"Reação animada com {effect.emoji}", inline=False)
    else:
        embed.add_field(name="Tipo", value="Efeito desconhecido", inline=False)

    await canal_logs.send(embed=embed)


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
        print(f"✅ Cargo '{cargo.name}' dado pra {membro} ({membro.id}).")
    except discord.Forbidden:
        print(
            f"⚠️ SEM PERMISSÃO pra dar o cargo '{cargo.name}' pra {membro}. "
            f"Rode /diagnostico-cargos no Discord pra confirmar se é permissão 'Gerenciar Cargos' "
            f"faltando ou hierarquia (cargo do Drax precisa estar ACIMA do '{cargo.name}')."
        )
    except discord.HTTPException as e:
        print(f"⚠️ Erro ao dar o cargo '{cargo.name}' pra {membro}: {e}")


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
        print(f"✅ Cargo '{cargo.name}' tirado de {membro} ({membro.id}).")
    except discord.Forbidden:
        print(
            f"⚠️ SEM PERMISSÃO pra tirar o cargo '{cargo.name}' de {membro}. "
            f"Rode /diagnostico-cargos no Discord pra confirmar se é permissão 'Gerenciar Cargos' "
            f"faltando ou hierarquia (cargo do Drax precisa estar ACIMA do '{cargo.name}')."
        )
    except discord.HTTPException as e:
        print(f"⚠️ Erro ao tirar o cargo '{cargo.name}' de {membro}: {e}")


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


@bot.tree.command(
    name="diagnostico-cargos",
    description="Mostra se cada cargo existe e se o Drax realmente consegue dar/tirar ele (permissão e hierarquia)",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def diagnostico_cargos(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    guild = interaction.guild
    bot_membro = guild.me
    cargo_mais_alto_bot = bot_membro.top_role
    tem_permissao = bot_membro.guild_permissions.manage_roles

    linhas = [
        f"{'✅' if tem_permissao else '❌'} Permissão **Gerenciar Cargos**: "
        + ("concedida" if tem_permissao else "FALTANDO — dê essa permissão ao cargo do Drax"),
        f"🐾 Cargo mais alto do Drax: **{cargo_mais_alto_bot.name}** (posição {cargo_mais_alto_bot.position})",
        "",
    ]

    problemas = {"hierarquia": False}

    def checar(nome_cargo: str) -> str:
        cargo = discord.utils.get(guild.roles, name=nome_cargo)
        if cargo is None:
            return f"❌ `{nome_cargo}` — não existe no servidor"
        if cargo.position >= cargo_mais_alto_bot.position:
            problemas["hierarquia"] = True
            return (
                f"⚠️ `{nome_cargo}` — existe, mas está ACIMA (ou igual) do cargo do Drax na "
                f"hierarquia, então ele NÃO consegue dar/tirar esse cargo"
            )
        return f"✅ `{nome_cargo}` — existe e o Drax consegue gerenciar"

    linhas.append(f"**Verificado:** {checar(config['cargo_verificado'])}")
    linhas.append("")
    linhas.append("**Painel de registro:**")
    for _nome, dados in config["cargos_registro"].items():
        linhas.append(checar(dados["cargo"]))

    texto = "\n".join(linhas)
    if len(texto) > 3900:
        texto = texto[:3900] + "\n… (lista cortada, muitos cargos — mas o padrão do problema já deve estar claro acima)"

    embed = discord.Embed(title="🩺 Diagnóstico de cargos do Drax", description=texto, color=COR_EMBED)
    if not tem_permissao or problemas["hierarquia"]:
        embed.set_footer(text="Dica: em Config. do Servidor > Cargos, arraste o cargo do Drax pra cima de todos os cargos que ele precisa gerenciar.")

    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(
    name="diagnostico-armazenamento",
    description="Confere se a configuração do Drax está mesmo sendo salva num Volume persistente do Railway",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def diagnostico_armazenamento(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    caminho_env = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    linhas = []

    if caminho_env:
        linhas.append(f"✅ Variável `RAILWAY_VOLUME_MOUNT_PATH` detectada: `{caminho_env}`")
        linhas.append("✅ Um Volume está anexado — a config DEVERIA estar persistindo entre restarts.")
    else:
        linhas.append("❌ Variável `RAILWAY_VOLUME_MOUNT_PATH` NÃO detectada.")
        linhas.append(
            "❌ Ou seja: a config NÃO é persistente agora — todo redeploy/restart apaga e "
            "recomeça do zero. É a causa mais provável dos painéis duplicando. Confira em "
            "**Settings > Volumes** se o Volume está anexado a ESTE serviço específico "
            "(não a outro serviço do mesmo projeto) e se você reiniciou/redeployou depois "
            "de criar ele."
        )

    linhas.append("")
    linhas.append(f"📄 Arquivo de configuração usado agora: `{ARQUIVO_CONFIG.resolve()}`")

    try:
        ARQUIVO_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        teste = ARQUIVO_CONFIG.parent / ".drax_teste_escrita"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        linhas.append("✅ Consegui escrever nessa pasta agora mesmo (permissão de escrita ok).")
    except Exception as e:
        linhas.append(f"❌ NÃO consegui escrever nessa pasta agora mesmo: {e}")

    if ARQUIVO_CONFIG.exists():
        modificado = datetime.fromtimestamp(ARQUIVO_CONFIG.stat().st_mtime)
        linhas.append(f"🕓 Última vez que o arquivo foi salvo: {modificado.strftime('%d/%m/%Y %H:%M:%S')}")
    else:
        linhas.append("⚠️ O arquivo de configuração ainda nem existe nesse caminho.")

    embed = discord.Embed(
        title="🩺 Diagnóstico de armazenamento do Drax", description="\n".join(linhas), color=COR_EMBED
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


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
    diagnostico_cargos,
    diagnostico_armazenamento,
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
