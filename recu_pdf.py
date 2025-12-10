from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime

def draw_separator(c, y):
    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.5)
    c.line(10*mm, y, 200*mm, y)

def generate_recu_A4_pdf(filepath, vente, boutique, client):
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    y = height - 20*mm

    # --- BOUTIQUE HEADER ---
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawCentredString(width/2, y, boutique['nom_boutique'])
    y -= 8*mm

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    if boutique["adresse"]:
        c.drawCentredString(width/2, y, boutique["adresse"])
        y -= 5*mm
    if boutique["telephone"]:
        c.drawCentredString(width/2, y, f"Téléphone : {boutique['telephone']}")
        y -= 5*mm

    y -= 8*mm
    draw_separator(c, y)
    y -= 10*mm

    # --- TITRE REÇU ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(10*mm, y, "💰 Reçu de vente")
    y -= 10*mm

    # --- DÉTAILS GÉNÉRAUX ---
    c.setFont("Helvetica", 10)
    c.drawString(10*mm, y, f"Référence : {vente['reference']}")
    y -= 5*mm
    c.drawString(10*mm, y, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 5*mm

    if client["nom"]:
        c.drawString(10*mm, y, f"Client : {client['nom']}")
        y -= 5*mm
    if client["telephone"]:
        c.drawString(10*mm, y, f"Téléphone client : {client['telephone']}")
        y -= 8*mm

    y -= 5*mm
    draw_separator(c, y)
    y -= 10*mm

    # --- TABLEAU PRODUITS ---
    c.setFont("Helvetica-Bold", 11)
    c.drawString(10*mm, y, "Article")
    c.drawString(90*mm, y, "Qté")
    c.drawString(120*mm, y, "PU")
    c.drawString(155*mm, y, "Total")
    y -= 7*mm

    c.setFont("Helvetica", 10)

    for item in vente["items"]:
        c.drawString(10*mm, y, item["nom"])
        c.drawString(90*mm, y, str(item["quantite"]))
        c.drawString(120*mm, y, f"{item['prix']:,} FCFA")
        c.drawString(155*mm, y, f"{item['total']:,} FCFA")
        y -= 6*mm

    y -= 8*mm
    draw_separator(c, y)
    y -= 12*mm

    # --- TOTAL ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#0A4D68"))
    c.drawString(10*mm, y, f"Montant total : {vente['montant_total']:,} FCFA")

    y -= 10*mm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(10*mm, y, f"Montant payé : {vente['montant_paye']:,} FCFA")
    y -= 8*mm
    c.drawString(10*mm, y, f"Monnaie rendue : {vente['monnaie_rendue']:,} FCFA")

    y -= 20*mm

    # --- SIGNATURE ---
    c.setFont("Helvetica", 10)
    c.drawString(10*mm, y, "Signature du vendeur :")
    y -= 20*mm
    c.line(10*mm, y, 80*mm, y)

    c.save()
