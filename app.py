import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime
import math
import csv
import os

DB = "parking.db"
LOG_FILE = "log.txt"
TARIFA_PRIMEIRA_HORA = 10.0
TARIFA_HORA_ADICIONAL = 8.0
PACOTE_12H = 35.0
DIARIA = 40.0
NUM_VAGAS = 30


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS vaga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        status TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ticket (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT,
        vaga_id INTEGER,
        entrada TEXT,
        saida TEXT,
        valor REAL
    )""")
    conn.commit()
    # inicializa as 30 vagas, se ainda não existirem
    c.execute("SELECT COUNT(*) FROM vaga")
    if c.fetchone()[0] == 0:
        for i in range(1, NUM_VAGAS + 1):
            c.execute("INSERT INTO vaga (codigo, status) VALUES (?,?)", (f'V{i}', 'livre'))
    conn.commit()
    conn.close()


def log_event(texto):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")


def buscar_vagas():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, codigo, status FROM vaga ORDER BY id")
    vagas = c.fetchall()
    conn.close()
    return vagas


def marcar_vaga_ocupada(vaga_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE vaga SET status = 'ocupada' WHERE id = ?", (vaga_id,))
    conn.commit()
    conn.close()


def marcar_vaga_livre(vaga_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE vaga SET status = 'livre' WHERE id = ?", (vaga_id,))
    conn.commit()
    conn.close()


def criar_ticket(placa, vaga_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO ticket (placa, vaga_id, entrada) VALUES (?,?,?)", (placa, vaga_id, entrada))
    conn.commit()
    conn.close()
    log_event(f"Entrada: placa {placa} -> vaga {vaga_id}")


def buscar_ticket_ativo_por_placa(placa):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, placa, vaga_id, entrada FROM ticket WHERE placa = ? AND saida IS NULL", (placa,))
    r = c.fetchone()
    conn.close()
    return r


def fechar_ticket(ticket_id, saida, valor):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE ticket SET saida = ?, valor = ? WHERE id = ?", (saida, valor, ticket_id))
    conn.commit()
    conn.close()


def calcular_valor(entrada_dt, saida_dt):
    diff = saida_dt - entrada_dt
    horas = math.ceil(diff.total_seconds() / 3600)
    if horas <= 1:
        return TARIFA_PRIMEIRA_HORA
    elif horas < 12:
        return TARIFA_PRIMEIRA_HORA + (horas - 1) * TARIFA_HORA_ADICIONAL
    elif horas == 12:
        return PACOTE_12H
    else:
        return DIARIA


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Controle de Estacionamento — Lohany Vilas Boas (Versão Didática)")
        self.geometry("1000x700")
        self.create_widgets()
        self.refresh_vagas()

    def create_widgets(self):
        top = ttk.Frame(self)
        top.pack(side='top', fill='x', padx=10, pady=10)

        ttk.Button(top, text="Registrar Entrada", command=self.registrar_entrada).pack(side='left', padx=5)
        ttk.Button(top, text="Registrar Saída", command=self.registrar_saida).pack(side='left', padx=5)
        ttk.Button(top, text="Relatórios (CSV)", command=self.export_csv).pack(side='left', padx=5)
        ttk.Button(top, text="Atualizar", command=self.refresh_vagas).pack(side='left', padx=5)
        ttk.Button(top, text="Configurações / Opções Avançadas", command=self.abrir_config).pack(side='left', padx=5)

        self.canvas = tk.Canvas(self, width=960, height=560)
        self.canvas.pack(padx=10, pady=10)
        self.vaga_buttons = []

    def refresh_vagas(self):
        for btn in self.vaga_buttons:
            btn.destroy()
        self.vaga_buttons = []
        vagas = buscar_vagas()
        cols = 6
        x0, y0 = 20, 20
        w, h = 140, 70
        for idx, (vid, codigo, status) in enumerate(vagas):
            r = idx // cols
            c = idx % cols
            x = x0 + c * (w + 10)
            y = y0 + r * (h + 10)
            color = "green" if status == "livre" else "red"
            btn = tk.Button(self.canvas, text=f"{codigo}\n{status}", bg=color, fg="white",
                            command=lambda v=vid: self.operar_vaga(v))
            self.canvas.create_window(x, y, anchor='nw', window=btn, width=w, height=h)
            self.vaga_buttons.append(btn)

    def operar_vaga(self, vaga_id):
        resp = messagebox.askquestion("Vaga", f"Deseja registrar entrada manual nesta vaga ({vaga_id})?")
        if resp == "yes":
            placa = simpledialog.askstring("Placa", "Digite a placa do veículo:").upper()
            if placa:
                criar_ticket(placa, vaga_id)
                marcar_vaga_ocupada(vaga_id)
                messagebox.showinfo("OK", f"Veículo {placa} registrado na vaga {vaga_id}.")
                self.refresh_vagas()

    def registrar_entrada(self):
        placa = simpledialog.askstring("Entrada", "Digite a placa do veículo:")
        if not placa:
            return
        placa = placa.upper()
        vagas = buscar_vagas()
        vaga_id = next((vid for vid, cod, status in vagas if status == "livre"), None)
        if vaga_id is None:
            messagebox.showwarning("Lotado", "Estacionamento cheio!")
            return
        criar_ticket(placa, vaga_id)
        marcar_vaga_ocupada(vaga_id)
        messagebox.showinfo("Entrada", f"Veículo {placa} estacionado na vaga {vaga_id}.")
        self.refresh_vagas()

    def registrar_saida(self):
        placa = simpledialog.askstring("Saída", "Digite a placa do veículo:")
        if not placa:
            return
        placa = placa.upper()
        ticket = buscar_ticket_ativo_por_placa(placa)
        if not ticket:
            messagebox.showerror("Erro", "Ticket não encontrado.")
            return
        ticket_id, placa_db, vaga_id, entrada_str = ticket
        entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S")
        saida_dt = datetime.now()
        valor = calcular_valor(entrada_dt, saida_dt)
        if messagebox.askyesno("Confirmar", f"Tempo: {saida_dt - entrada_dt}\nValor: R$ {valor:.2f}\nConfirmar saída?"):
            fechar_ticket(ticket_id, saida_dt.strftime("%Y-%m-%d %H:%M:%S"), valor)
            marcar_vaga_livre(vaga_id)
            messagebox.showinfo("Saída", f"Saída registrada. Valor: R$ {valor:.2f}")
            log_event(f"Saída: placa {placa} -> valor R${valor:.2f}")
            self.refresh_vagas()

    def export_csv(self):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT placa, vaga_id, entrada, saida, valor FROM ticket")
        rows = c.fetchall()
        conn.close()
        with open("relatorio_tickets.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Placa", "Vaga", "Entrada", "Saída", "Valor (R$)"])
            writer.writerows(rows)
        messagebox.showinfo("Exportado", "Relatório CSV gerado com sucesso (relatorio_tickets.csv).")

    def abrir_config(self):
        win = tk.Toplevel(self)
        win.title("Configurações / Opções Avançadas")
        ttk.Button(win, text="🔄 Zerar Banco de Dados", command=self.zerar_banco).pack(pady=10)
        ttk.Button(win, text="📈 Ver Resumo Financeiro", command=self.resumo).pack(pady=10)
        ttk.Button(win, text="🧾 Abrir Log de Operações", command=lambda: os.startfile(LOG_FILE)).pack(pady=10)

    def zerar_banco(self):
        if not messagebox.askyesno("Confirmação", "Deseja realmente apagar todos os tickets e liberar as vagas?"):
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM ticket")
        c.execute("UPDATE vaga SET status='livre'")
        conn.commit()
        conn.close()
        log_event("Banco de dados zerado pelo usuário.")
        messagebox.showinfo("OK", "Banco de dados zerado com sucesso!")
        self.refresh_vagas()

    def resumo(self):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(valor) FROM ticket WHERE saida IS NOT NULL")
        qtd, total = c.fetchone()
        conn.close()
        total = total or 0
        messagebox.showinfo("Resumo", f"Total de veículos atendidos: {qtd}\nTotal arrecadado: R$ {total:.2f}")


if __name__ == '__main__':
    init_db()
    app = App()
    app.mainloop()
