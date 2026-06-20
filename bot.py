from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
import sqlite3
from datetime import datetime

TOKEN = "8664960661:AAEYKkX9VcZLy7jvWyAq6a5cU8DwIaw7MnA"

conn = sqlite3.connect("keuangan.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS transaksi(
id INTEGER PRIMARY KEY AUTOINCREMENT,
tanggal TEXT,
pengguna TEXT,
jenis TEXT,
kategori TEXT,
jumlah INTEGER,
keterangan TEXT
)
""")
conn.commit()

PENGGUNA, JENIS, KATEGORI, JUMLAH, KETERANGAN, RESET = range(6)

def simpan_transaksi(pengguna, jenis, kategori, jumlah, keterangan):
    tanggal = datetime.now().strftime("%d-%m-%Y %H:%M")
    cur.execute(
        "INSERT INTO transaksi (tanggal,pengguna,jenis,kategori,jumlah,keterangan) VALUES (?,?,?,?,?,?)",
        (tanggal, pengguna, jenis, kategori, jumlah, keterangan)
    )
    conn.commit()

def total(pengguna, jenis):
    cur.execute("SELECT COALESCE(SUM(jumlah),0) FROM transaksi WHERE pengguna=? AND jenis=?",
                (pengguna, jenis))
    return cur.fetchone()[0]

def saldo_pengguna(pengguna):
    return total(pengguna, "Masuk") - total(pengguna, "Keluar")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["Konter"], ["Reva"]]
    await update.message.reply_text(
        "Pilih Pengguna",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return PENGGUNA

async def pilih_pengguna(update, context):
    context.user_data["pengguna"] = update.message.text
    await update.message.reply_text(
        "Pilih Transaksi",
        reply_markup=ReplyKeyboardMarkup([["Masuk"], ["Keluar"]], resize_keyboard=True)
    )
    return JENIS

async def pilih_jenis(update, context):
    pengguna = context.user_data["pengguna"]
    jenis = update.message.text
    context.user_data["jenis"] = jenis

    if pengguna == "Konter":
        kb = [["Laba"]] if jenis == "Masuk" else [["Pengeluaran Konter"]]
    else:
        kb = [["Gaji"], ["Lainnya"]] if jenis == "Masuk" else [["Makan"], ["Pribadi"]]

    await update.message.reply_text(
        "Pilih Kategori",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return KATEGORI

async def pilih_kategori(update, context):
    context.user_data["kategori"] = update.message.text
    await update.message.reply_text("Masukkan jumlah:", reply_markup=ReplyKeyboardRemove())
    return JUMLAH

async def input_jumlah(update, context):
    try:
        context.user_data["jumlah"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Masukkan angka saja.")
        return JUMLAH

    await update.message.reply_text("Masukkan keterangan:")
    return KETERANGAN

async def input_keterangan(update, context):
    simpan_transaksi(
        context.user_data["pengguna"],
        context.user_data["jenis"],
        context.user_data["kategori"],
        context.user_data["jumlah"],
        update.message.text
    )

    await update.message.reply_text(
        "✅ Tersimpan!\n\nKetik /start untuk transaksi baru."
    )
    return ConversationHandler.END

async def saldo(update, context):
    await update.message.reply_text(
        f"💰 SALDO\n\n"
        f"Konter: Rp{saldo_pengguna('Konter'):,}\n"
        f"Reva: Rp{saldo_pengguna('Reva'):,}"
    )

async def laporan(update, context):
    pesan = "📊 LAPORAN KEUANGAN\n\n"
    for p in ["Konter", "Reva"]:
        masuk = total(p, "Masuk")
        keluar = total(p, "Keluar")
        saldo = masuk - keluar
        pesan += (
            f"👤 {p}\n"
            f"📈 Masuk : Rp{masuk:,}\n"
            f"📉 Keluar: Rp{keluar:,}\n"
            f"💰 Saldo : Rp{saldo:,}\n\n"
        )
    await update.message.reply_text(pesan)

async def riwayat(update, context):
    cur.execute("""
    SELECT tanggal,pengguna,jenis,kategori,jumlah,keterangan
    FROM transaksi
    ORDER BY id DESC LIMIT 10
    """)
    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("Belum ada transaksi.")
        return

    teks = "📋 RIWAYAT\n\n"
    for r in rows:
        teks += f"{r[0]}\n{r[1]} | {r[2]} | {r[3]}\nRp{r[4]:,}\n{r[5]}\n\n"

    await update.message.reply_text(teks)

async def cancel(update, context):
    await update.message.reply_text("Dibatalkan.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def backup(update, context):

    try:

        with open(
            "keuangan.db",
            "rb"
        ) as db:

            await update.message.reply_document(
                document=db,
                filename="keuangan.db"
            )

    except Exception as e:

        await update.message.reply_text(
            f"Error: {e}"
        )

async def export(update, context):

    cur.execute("""
    SELECT
    tanggal,
    pengguna,
    jenis,
    kategori,
    jumlah,
    keterangan
    FROM transaksi
    ORDER BY id DESC
    """)

    data = cur.fetchall()

    if not data:

        await update.message.reply_text(
            "Belum ada data."
        )

        return

    with open(
        "laporan.csv",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "Tanggal,Pengguna,Jenis,Kategori,Jumlah,Keterangan\n"
        )

        for row in data:

            f.write(
                f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}\n"
            )

    await update.message.reply_document(
        document=open(
            "laporan.csv",
            "rb"
        )
    )
async def menu(update, context):

    await update.message.reply_text(
        """
📋 MENU

/start
/saldo
/laporan
/riwayat
/export
/backup
"""
    )
async def reset(update, context):

    keyboard = [
        ["YA RESET"],
        ["BATAL"]
    ]

    await update.message.reply_text(
        "⚠️ Yakin ingin menghapus semua data?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

    return RESET
async def konfirmasi_reset(
    update,
    context
):

    pilihan = update.message.text

    if pilihan == "YA RESET":

        cur.execute(
            "DELETE FROM transaksi"
        )

        conn.commit()

        await update.message.reply_text(
            "✅ Semua data berhasil dihapus.",
            reply_markup=ReplyKeyboardRemove()
        )

    else:

        await update.message.reply_text(
            "❌ Reset dibatalkan.",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END
    
app = Application.builder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        PENGGUNA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_pengguna)
        ],
        JENIS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_jenis)
        ],
        KATEGORI: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_kategori)
        ],
        JUMLAH: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, input_jumlah)
        ],
        KETERANGAN: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, input_keterangan)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ]
)

reset_conv = ConversationHandler(
    entry_points=[
        CommandHandler("reset", reset)
    ],
    states={
        RESET: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                konfirmasi_reset
            )
        ]
    },
    fallbacks=[]
)

app.add_handler(conv)
app.add_handler(reset_conv)
app.add_handler(CommandHandler("saldo", saldo))
app.add_handler(CommandHandler("laporan", laporan))
app.add_handler(CommandHandler("riwayat", riwayat))
app.add_handler(
    CommandHandler(
        "backup",
        backup
    )
)
app.add_handler(
    CommandHandler(
        "export",
        export
    )
)

app.add_handler(
    CommandHandler(
        "menu",
        menu
    )
)
print("Bot berjalan...")
app.run_polling()
