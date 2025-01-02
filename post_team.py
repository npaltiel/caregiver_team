from APIkeys import app_name, app_secret, app_key
import math
import xml.etree.ElementTree as ET
from get_requests import get_caregiver_id
from asynchronous import retry_soap_request


def get_employment_types(caregiver):
    segment_start = '<Discipline>'
    segment_end = '</Discipline>\n'
    types = caregiver['Employment Type'].split(', ')

    res = ''
    for type in types:
        res += f"{segment_start}{type}{segment_end}"

    return res.rstrip('\n')


async def update_team(caregiver, team):
    caregiver_code = caregiver['Caregiver Code - Office']
    try:
        caregiver_id = await get_caregiver_id(caregiver_code)
        employment_types = get_employment_types(caregiver)

        rehire = '<RehireDate>' + caregiver['Rehire Date'] + '</RehireDate>' if isinstance(caregiver['Rehire Date'],
                                                                                           str) or not math.isnan(
            caregiver['Rehire Date']) else ""

        # Define the XML payload with correct SOAP 1.1 envelope for Search Visits
        payload = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <UpdateCaregiverDemographics xmlns="https://www.hhaexchange.com/apis/hhaws.integration">
              <Authentication>
                <AppName>{app_name}</AppName>
                <AppSecret>{app_secret}</AppSecret>
                <AppKey>{app_key}</AppKey>
              </Authentication>
              <CaregiverInfo>
                <CaregiverID>{caregiver_id}</CaregiverID>
                <FirstName>{caregiver['First Name']}</FirstName>
                <LastName>{caregiver['Last Name']}</LastName>
                <Gender>{caregiver['Gender']}</Gender>
                <BirthDate>{caregiver['DOB']}</BirthDate>
                <SSN>{caregiver['SSN']}</SSN>
                {rehire}
                <StatusID>1</StatusID>
                <EmploymentTypes>{employment_types}</EmploymentTypes>
                <ApplicationDate>{caregiver['Application Date']}</ApplicationDate>
                <TeamID>{team}</TeamID>
                <HHAPCARegistryNumber>{caregiver['HHA/PCA Registry Number']}</HHAPCARegistryNumber>
                <Address>
                  <Zip5>{int(caregiver['Zip'])}</Zip5>
                </Address>
                <NotificationPreferences>
                  <MethodID>{caregiver['Notification ID']}</MethodID>
                  <MobileOrSMS>{caregiver['Mobile/Text Message']}</MobileOrSMS>
                </NotificationPreferences>
                <EmployeeType>Employee</EmployeeType>
              </CaregiverInfo>
            </UpdateCaregiverDemographics>
          </soap:Body>
        </soap:Envelope>"""

        response_content = await retry_soap_request('https://app.hhaexchange.com/integration/ent/v1.8/ws.asmx', payload,
                                                    '"https://www.hhaexchange.com/apis/hhaws.integration/UpdateCaregiverDemographics"')
        # Check response content for success (you may want to look for specific elements in `response_content` if needed)
        if "Success" in response_content:  # Replace "Success" with the actual success check from response
            return caregiver_code, True, None
        else:
            # Extract error message from response (you may need to parse the XML response)
            root = ET.fromstring(response_content)
            error_message_element = root.find('.//ns1:ErrorMessage',
                                              namespaces={'ns1': 'https://www.hhaexchange.com/apis/hhaws.integration'})

            error_message = error_message_element.text if error_message_element is not None and error_message_element.text else "No error message provided"
            return caregiver_code, False, error_message

    except Exception as e:
        # Return error message if an exception occurs
        error_message = str(e)
        return caregiver_code, False, error_message
