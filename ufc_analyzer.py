from datetime import datetime
import math
import requests

def normal_cdf(x, mu, sigma):
    try:
        return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))
    except:
        return 0.5

def calcular_cuotas(prob):
    try:
        if prob <= 1.0: prob = 1.0
        if prob >= 95.0: prob = 95.0
        decimal = round(100.0 / (prob * 1.05), 2)
        return f"{max(1.10, decimal)}"
    except:
        return "1.90"

def calcular_cuotas_valor(prob):
    try:
        if prob <= 1.0: prob = 1.0
        decimal = round(100.0 / (prob * 1.02), 2)
        return f"{max(1.75, decimal)}"
    except:
        return "2.20"

def extraer_estadisticas_luchador(fighter_data):
    """Extrae estrictamente las estadísticas de rendimiento y récord oficial del peleador."""
    striking_acc = 50.0
    takedown_acc = 40.0
    win_pct = 0.500
    wins, losses = 0, 1
    
    try:
        # Extraer estadísticas de combate si están disponibles
        stats = fighter_data.get("statistics", [])
        for s in stats:
            name = s.get("name", "")
            val = float(s.get("value", 50))
            if name in ["strikingAccuracy", "significantStrikeAccuracy"]:
                striking_acc = val
            elif name in ["takedownAccuracy", "grapplingAccuracy"]:
                takedown_acc = val

        # Extraer récord oficial (W-L)
        records = fighter_data.get("records", [])
        if not records and "record" in fighter_data:
            records = [fighter_data.get("record")]

        for rec in records:
            summary = rec.get("summary", "0-1")
            partes = summary.replace("W", "").replace("L", "").replace("D", "").split("-")
            if len(partes) >= 2:
                wins = int(partes[0])
                losses = int(partes[1])
                total = wins + losses
                if total > 0:
                    win_pct = wins / total
                    break
    except Exception:
        pass

    return float(striking_acc), float(takedown_acc), float(win_pct), wins, losses

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        return dt_utc.strftime("%d/%m/%Y - %H:%M UTC")
    except Exception:
        return "📅 Próximamente"

def analizar_carteleras_ufc():
    print("🥊 Escaneando carteleras múltiples de UFC con modelo sabermétrico de combate...", flush=True)
    analisis_lista = []
    picks_vip_seguros = []
    picks_vip_valor = []
    
    url = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
    
    try:
        response = requests.get(url, timeout=5.0)
        if response.status_code != 200:
            return {"partidos": [], "picks_vip": []}
            
        data = response.json()
        events = data.get("events", [])
        
        # Escaneo de múltiples eventos (UFC 334, 335, 336 y eventos en cartelera)
        for event in events:
            event_name = event.get("name", "UFC Event")
            event_date_str = event.get("date", "")
            fecha_col = convertir_hora_colombia(event_date_str)
            
            competitions = event.get("competitions", [])
            for comp in competitions:
                competitors = comp.get("competitors", [])
                if len(competitors) < 2: continue
                
                f1_data = competitors[0]
                f2_data = competitors[1]
                
                f1_name = f1_data.get("athlete", {}).get("displayName", "Peleador 1")
                f2_name = f2_data.get("athlete", {}).get("displayName", "Peleador 2")
                
                # Extracción rigurosa basada en datos reales
                strike_1, td_1, wp_1, w1, l1 = extraer_estadisticas_luchador(f1_data)
                strike_2, td_2, wp_2, w2, l2 = extraer_estadisticas_luchador(f2_data)

                # Modelo sabermétrico de combate cruzado (Striking + Grappling + Inercia de Récord)
                eficiencia_1 = (strike_1 * 0.6) + (td_1 * 0.4) + (wp_1 * 20.0)
                eficiencia_2 = (strike_2 * 0.6) + (td_2 * 0.4) + (wp_2 * 20.0)
                
                delta_combate = eficiencia_1 - eficiencia_2
                
                # Desviación estándar típica para peleas de MMA (escala 15.0)
                prob_f1_win = (1.0 - normal_cdf(0, delta_combate, 15.0)) * 100.0
                p_f1 = round(max(15.0, min(85.0, prob_f1_win)), 1)
                p_f2 = round(100.0 - p_f1, 1)

                prob_ml = max(p_f1, p_f2)
                pick_val = f1_name if p_f1 >= p_f2 else f2_name
                cuota_ml = calcular_cuotas_valor(prob_ml)

                oportunidades = [
                    f"• 🥋 **Moneyline ({pick_val}):** {prob_ml}% | Cuota: *{cuota_ml}* ⏳",
                    f"• 📊 **Récord Oficial:** {f1_name} ({w1}-{l1}) vs {f2_name} ({w2}-{l2})",
                    f"• ⚡ **Eficiencia Strike/Grapple:** {f1_name} ({strike_1:.1f}% / {td_1:.1f}%) vs {f2_name} ({strike_2:.1f}% / {td_2:.1f}%)"
                ]

                str_oportunidades = "\n".join(oportunidades)

                mensaje = (
                    f"⚡ **ANÁLISIS SABERMÉTRICO UFC / MMA**\n"
                    f"🏟 **{event_name}**\n"
                    f"⚔️ *{f1_name}* vs. *{f2_name}*\n"
                    f"⏰ **Fecha/Hora:** {fecha_col}\n\n"
                    f"🎯 **Desglose Estadístico de Combate:**\n"
                    f"{str_oportunidades}"
                )

                analisis_lista.append({
                    "tipo": "partido", 
                    "partido": f"{f1_name} vs {f2_name}", 
                    "mensaje": mensaje, 
                    "is_final": False
                })

    except Exception as e:
        print(f"Error procesando carteleras UFC: {e}")

    return {"partidos": analisis_lista, "picks_vip": picks_vip_seguros}
