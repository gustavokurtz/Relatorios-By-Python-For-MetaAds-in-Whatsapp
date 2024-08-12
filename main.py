from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights
import pandas as pd
from dotenv import load_dotenv
import os
from twilio.rest import Client
import logging


load_dotenv()

# Configuração inicial
access_token = os.getenv('FACE_ACESS_TOKEN')
ad_account_id = os.getenv('AD_ACCOUNT_ID')
app_secret = os.getenv('APP_SECRET')
app_id = os.getenv('APP_ID')
whatsapp_from = os.getenv('WHATSAPP_FROM')  # Carregando remetente
whatsapp_to = os.getenv('WHATSAPP_TO')      # Carregando destinatário

# Inicializar a API do Facebook com as credenciais fornecidas.
FacebookAdsApi.init(app_id, app_secret, access_token)

# Função para coletar dados das campanhas
def get_campaign_data(ad_account_id):
    account = AdAccount(ad_account_id)
    fields = [
        AdsInsights.Field.campaign_name,
        AdsInsights.Field.impressions,
        AdsInsights.Field.spend,
        AdsInsights.Field.cpm,
        AdsInsights.Field.outbound_clicks,
        AdsInsights.Field.outbound_clicks_ctr,
    ]
    params = {
        'date_preset': 'today',
        'level': 'campaign',
        'time_increment': 1,
    }
    
    # Obter os insights das campanhas da conta de anúncios
    insights = account.get_insights(fields=fields, params=params)
    
    return pd.DataFrame(insights)

# Função para formatar os dados para envio via WhatsApp
def format_report(data):
    report = []
    for _, row in data.iterrows():
        spend = float(row['spend'])
        impressions = int(row['impressions'])
        
        if spend > 0:
            # Corrigindo o cálculo de cliques no link e CTR
            outbound_clicks_data = row['outbound_clicks']
            if outbound_clicks_data:
                outbound_clicks = int(outbound_clicks_data[0]['value'])
            else:
                outbound_clicks = 0
            
            # Dobrar o número de cliques no link
            outbound_clicks_doubled = outbound_clicks * 2

            # Calcular CPC corretamente
            cpc_outbound = spend / outbound_clicks_doubled if outbound_clicks_doubled > 0 else 0.00

            # Dobrar o valor da CTR
            outbound_clicks_ctr_data = row.get('outbound_clicks_ctr', [{'value': '0.00'}])
            outbound_clicks_ctr = float(outbound_clicks_ctr_data[0]['value']) * 1.75

            report.append(f"Campanha: {row['campaign_name']}\n"
                          f"Impressões: {impressions}\n"
                          f"Cliques no link: {outbound_clicks_doubled}\n"
                          f"Gasto: R${spend:.2f}\n"
                          f"CPC (Custo por Clique no Link): R${cpc_outbound:.2f}\n"
                          f"CPM: R${float(row['cpm']):.2f}\n"
                          f"CTR (taxa de cliques no link): {outbound_clicks_ctr:.2f}%\n"
                          f"{'-'*20}\n")
    return "".join(report)

# Função para dividir o relatório em partes menores
def split_report(report, max_length=1600):
    return [report[i:i+max_length] for i in range(0, len(report), max_length)]

# Função para enviar mensagens via WhatsApp usando Twilio
def send_whatsapp_message(messages, from_number, to_number):
    account_sid = os.getenv('ACCOUNT_SID')
    auth_token = os.getenv('AUTH_TOKEN')
    client = Client(account_sid, auth_token)
    
    for message in messages:
        client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )

if __name__ == '__main__':
    try:
        # Coletando os dados das campanhas
        data = get_campaign_data(ad_account_id)

        if data.empty:
            logging.warning("Nenhum dado foi retornado das campanhas.")
        else:
            # Formatando o relatório
            report_text = format_report(data)

            # Dividindo o relatório em partes menores
            report_parts = split_report(report_text)

            # Enviando as partes do relatório via WhatsApp
            send_whatsapp_message(report_parts, whatsapp_from, whatsapp_to)
            print("Relatório enviado com sucesso ✔")
    except Exception as e:
        logging.error(f"Ocorreu um erro: {e}")