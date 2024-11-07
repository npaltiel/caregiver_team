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
active_caregivers['Hire Date'] = pd.to_datetime(active_caregivers['Hire Date'])
active_caregivers['First Work Date'] = pd.to_datetime(active_caregivers['First Work Date'])
active_caregivers['Last Work Date'] = pd.to_datetime(active_caregivers['Last Work Date'])

df_notes = pd.read_csv(
    "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\Caregiver Notes (60 Days).csv")
df_notes['Date'] = pd.to_datetime(df_notes['Date'])
df_notes = df_notes.rename(columns={'Date': 'Discipline Date'})

# Define the conditions and choices for Discipline Expiry Date
conditions = [
    df_notes['Subject'] == 'Disciplinary Verbal',
    df_notes['Subject'] == 'Disciplinary Written 1',
    df_notes['Subject'] == 'Disciplinary Written 2'
]

# Define the number of days to add based on the conditions
choices = [
    df_notes['Discipline Date'] + pd.Timedelta(days=30),
    df_notes['Discipline Date'] + pd.Timedelta(days=60),
    df_notes['Discipline Date'] + pd.Timedelta(days=90)
]

# Create the Expiry Date column based on conditions
df_notes['Expiry Date'] = np.select(conditions, choices, default=pd.NaT)

df_notes_filtered = df_notes.dropna(subset=['Expiry Date'])

# Find the row index of the max Expiry Date within each group
idx = df_notes_filtered.groupby('Caregiver Code - Office')['Expiry Date'].idxmax()

# Use the index to select the corresponding Discipline Date and Expiry Date
latest_expiry = df_notes.loc[idx, ['Caregiver Code - Office', 'Discipline Date', 'Expiry Date']].reset_index(drop=True)

# idx = df_notes.groupby('Caregiver Code - Office')['Expiry Date'].idxmax()
# # Use the index to select the corresponding Date and Expiry Date
# latest_expiry = df_notes.loc[idx, ['Caregiver Code - Office', 'Discipline Date', 'Expiry Date']].reset_index(drop=True)
latest_expiry['Expiry Date'] = pd.to_datetime(latest_expiry['Expiry Date']).dt.date

active_caregivers = pd.merge(active_caregivers, latest_expiry, on='Caregiver Code - Office',
                             how='left')
active_caregivers['Disciplinary'] = np.where(
    (
            active_caregivers['Expiry Date'].isnull() &
            (active_caregivers['Last Work Date'] > (datetime.today() - timedelta(days=90)))
    )
    |
    (
            active_caregivers['Expiry Date'].isnull() &
            (active_caregivers['Team'] != 'Tier 2')
    )
    |
    (
            (active_caregivers['Expiry Date'] <= datetime.today().date()) &
            (active_caregivers['Last Work Date'] > active_caregivers['Discipline Date'])
    ),
    False,
    True
)

# Those that are not on probation but should be
prob_date = []
for i in range(len(active_caregivers)):
    if active_caregivers['First Work Date'][i] >= active_caregivers['Hire Date'][i] or pd.isnull(
            active_caregivers['First Work Date'][i]):
        prob_date.append(active_caregivers['First Work Date'][i])
    elif active_caregivers['First Work Date'][i] < active_caregivers['Hire Date'][i] and \
            active_caregivers['Last Work Date'][i] >= active_caregivers['Hire Date'][i]:
        prob_date.append(active_caregivers['Hire Date'][i])
    else:
        prob_date.append(datetime.today())

active_caregivers['Probation Start Date'] = prob_date

make_probation = active_caregivers[
    (active_caregivers['Team'] != "Probation") & (active_caregivers['Disciplinary'] == False) & ((
                                                                                                         active_caregivers[
                                                                                                             'Probation Start Date'] >= (
                                                                                                                 datetime.today() - timedelta(
                                                                                                             days=30))) | pd.isnull(
        active_caregivers['Probation Start Date']))].copy().reset_index(drop=True)

# Those that are on probation but should be moved to Tier 1
make_tier1 = active_caregivers[(active_caregivers['Team'] == 'Probation') & (active_caregivers[
                                                                                 'Probation Start Date'] < (
                                                                                     datetime.today() - timedelta(
                                                                                 days=30))) & (
                                       active_caregivers['Disciplinary'] == False)].copy().reset_index(drop=True)

# Those that should be moved to Tier 2
make_tier2 = active_caregivers[(active_caregivers['Team'] != 'Tier 2') & (
        active_caregivers['Disciplinary'] == True)].copy().reset_index(drop=True)

# Those that should be moved back to Tier 1
back_to_1 = active_caregivers[(active_caregivers['Team'] == 'Tier 2') & (
        active_caregivers['Disciplinary'] == False)].copy().reset_index(drop=True)

make_tier1 = pd.concat([make_tier1, back_to_1], ignore_index=True)
