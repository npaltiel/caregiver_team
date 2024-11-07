import APIkeys
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import asyncio
import aiohttp
import pandas as pd
import numpy as np
import sqlite3
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

app_name = APIkeys.app_name
app_secret = APIkeys.app_secret
app_key = APIkeys.app_key

df_caregivers = pd.read_csv(
    "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\List of Caregivers (Quality).csv")
active_caregivers = df_caregivers[
    (df_caregivers['Status'] == "Active") & (df_caregivers['Type'] == 'Employee')].copy().reset_index(drop=True)
df_notes = pd.read_csv(
    "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\Caregiver Notes (60 Days).csv")

data = pd.merge(df_notes, df_caregivers, on=['Caregiver Code - Office'],
                how='left')

active_caregivers['Disciplinary'] = active_caregivers['Caregiver Code - Office'].isin(
    df_notes['Caregiver Code - Office'])

# Check Probation rules
# Those that are not on probation but should be
active_caregivers['First Work Date'] = pd.to_datetime(active_caregivers['First Work Date'])
active_caregivers['Hire Date'] = pd.to_datetime(active_caregivers['Hire Date'])
active_caregivers['Probation Start Date'] = [
    active_caregivers['First Work Date'][i] if active_caregivers['First Work Date'][i] >=
                                               active_caregivers['Hire Date'][i] or
                                               pd.isnull(active_caregivers['First Work Date'][i]) else
    active_caregivers['Hire Date'][i] for i in range(len(active_caregivers))]
make_probation = active_caregivers[
    (active_caregivers['Team'] != "Probation") & (active_caregivers['Disciplinary'] == False) & ((
                                                                                                         active_caregivers[
                                                                                                             'Probation Start Date'] > (
                                                                                                                 datetime.today() - timedelta(
                                                                                                             days=30))) | pd.isnull(
        active_caregivers['Probation Start Date']))].reset_index(drop=True)
