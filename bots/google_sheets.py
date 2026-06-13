from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = '1A1BdsHJIMGhMgqSs2jEK98GeMVJh8t6xyFVanMWlRo4'
SERVICE_ACCOUNT_FILE = 'bots/sacc.json'

def get_google_sheets_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def write_to_google_sheets(phone_number, name, trip_details):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()

    trip_data = [
        trip_details.get("trip_direction"),
        trip_details.get("people_number"),
        trip_details.get("travel_dates"),
        trip_details.get("budget"),
        trip_details.get("customer_wishes")
    ]

    values = [trip_data + [phone_number, name]]

    body = {'values': values}

    try:
        result = sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Sheet1!A2:G2",
            valueInputOption="RAW",
            body=body
        ).execute()
        print("Данные успешно записаны в Google Sheets.")
        return result
    except Exception as error:
        print(f"Ошибка записи в Google Sheets: {error}")
