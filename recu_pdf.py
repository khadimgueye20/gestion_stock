from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime

def draw_separator(c, y):
    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.5)
    c.line(10 * mm, y, 200 * mm, y)

def generate_recu_A4_pdf(output, vente, boutique, client):
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    # En-tête boutique
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawCentredString(width / 2, y, boutique.get("nom_boutique", "Ma Boutique"))
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)

    if boutique.get("adresse"):
        c.drawCentredString(width / 2, y, boutique["adresse"])
        y -= 5 * mm

    if boutique.get("telephone"):
        c.drawCentredString(width / 2, y, f"Téléphone : {boutique['telephone']}")
        y -= 5 * mm

    y -= 8 * mm
    draw_separator(c, y)
    y -= 10 * mm

    # Titre
    c.setFont("Helvetica-Bold", 14)
    c.drawString(10 * mm, y, "Reçu de vente")
    y -= 10 * mm

    # Infos générales
    c.setFont("Helvetica", 10)
    c.drawString(10 * mm, y, f"Référence : {vente.get('reference', '')}")
    y -= 5 * mm

    date_recu = vente.get("date_creation")
    if date_recu:
        date_str = date_recu.strftime("%d/%m/%Y %H:%M")
    else:
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    c.drawString(10 * mm, y, f"Date : {date_str}")
    y -= 5 * mm

    if client.get("nom"):
        c.drawString(10 * mm, y, f"Client : {client['nom']}")
        y -= 5 * mm

    if client.get("telephone"):
        c.drawString(10 * mm, y, f"Téléphone client : {client['telephone']}")
        y -= 5 * mm

    if client.get("adresse_livraison"):
        c.drawString(10 * mm, y, f"Adresse de livraison : {client['adresse_livraison']}")
        y -= 5 * mm

    y -= 5 * mm
    draw_separator(c, y)
    y -= 10 * mm

    # Tableau produits
    c.setFont("Helvetica-Bold", 11)
    c.drawString(10 * mm, y, "Article")
    c.drawString(90 * mm, y, "Qté")
    c.drawString(120 * mm, y, "PU")
    c.drawString(155 * mm, y, "Total")
    y -= 7 * mm

    c.setFont("Helvetica", 10)

    for item in vente.get("items", []):
        c.drawString(10 * mm, y, str(item.get("nom", ""))[:35])
        c.drawString(90 * mm, y, str(item.get("quantite", 0)))
        c.drawString(120 * mm, y, f"{float(item.get('prix', 0)):,.0f} FCFA")
        c.drawString(155 * mm, y, f"{float(item.get('total', 0)):,.0f} FCFA")
        y -= 6 * mm

        if y < 60 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica", 10)

    y -= 8 * mm
    draw_separator(c, y)
    y -= 12 * mm

    # Totaux
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(10 * mm, y, f"Montant produits : {float(vente.get('montant_produits', 0)):,.0f} FCFA")
    y -= 8 * mm

    c.drawString(10 * mm, y, f"Prix de livraison : {float(vente.get('prix_livraison', 0)):,.0f} FCFA")
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#0A4D68"))
    c.drawString(10 * mm, y, f"Montant total : {float(vente.get('montant_total', 0)):,.0f} FCFA")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(10 * mm, y, f"Montant payé : {float(vente.get('montant_paye', 0)):,.0f} FCFA")
    y -= 8 * mm

    c.drawString(10 * mm, y, f"Monnaie rendue : {float(vente.get('monnaie_rendue', 0)):,.0f} FCFA")
    y -= 20 * mm

    # Signature
    c.setFont("Helvetica", 10)
    c.drawString(10 * mm, y, "Signature du vendeur :")
    y -= 20 * mm
    c.line(10 * mm, y, 80 * mm, y)

    c.save()