import logging
import warnings

import numpy as np
from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.errors import HttpError


def get_data_from_sheet(credentials: str, spreadsheet_id: str, cells_range='A1:G1000') -> dict | None:
    logger = logging.getLogger('google_api')
    # Load the credentials from the JSON key file
    credentials = service_account.Credentials.from_service_account_file(credentials)

    # Create a service client
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)

    # Call the Sheets API to get the values
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings('error', category=np.VisibleDeprecationWarning)
            # Call the Sheets API to get the values
            result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=cells_range).execute()
            values = result.get('values', [])
            logger.info(f"Data successfully parsed from google sheet with sheet_id: {spreadsheet_id}")
            title, *values = values
            names = set(np.array(values).transpose()[0])
            dict_values = {}
            for name in names:
                dict_values[name] = {"reschedule": [],
                                     "group_id": set()
                                     }
            for i in values:
                dict_values[i[0]]['reschedule'].append(i[1:])
                dict_values[i[0]]['group_id'].add(i[-1])

            return dict_values

    except (HttpError, np.VisibleDeprecationWarning) as error:
        logger.error(f'An error occurred: {error}')
        if "Creating an ndarray from ragged nested sequences" in error:
            return {"error": f"{error} - ЭТО ОЗНАЧАЕТ ЧТО В ЭКЗЕЛЬ ФАЙЛЕ ПРОПУШЕНЫ КАКИЕ ТО НУЖНЫЕ ПОЛЯ"}
        return {"error": error}


