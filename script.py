import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import asyncio
from get_requests import get_teams, get_notification_methods
from post_team import update_team


async def main():
    df_caregivers = pd.read_csv(
        "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\List of Caregivers (Quality).csv")

    # Get only active employees and format the dataframe where relevant
    active_caregivers = df_caregivers[
        (df_caregivers['Status'] == "Active") &
        (df_caregivers['Type'] == 'Employee') &
        (~df_caregivers['Caregiver Code - Office'].str.contains("CDP", na=False)) &
        (~df_caregivers['Caregiver Code - Office'].str.contains("ANS", na=False)) &
        (~df_caregivers['Caregiver Code - Office'].str.contains("OHZ", na=False))
        ].copy().reset_index(drop=True)

    active_caregivers['Hire Date'] = pd.to_datetime(active_caregivers['Hire Date'])
    active_caregivers['Rehire Date'] = pd.to_datetime(active_caregivers['Rehire Date']).dt.strftime('%Y-%m-%d')
    active_caregivers['First Work Date'] = pd.to_datetime(active_caregivers['First Work Date'])
    active_caregivers['Last Work Date'] = pd.to_datetime(active_caregivers['Last Work Date'])
    active_caregivers['DOB'] = pd.to_datetime(active_caregivers['DOB']).dt.strftime('%Y-%m-%d')
    active_caregivers['Application Date'] = pd.to_datetime(active_caregivers['Application Date']).dt.strftime(
        '%Y-%m-%d')

    problematic_codes = ['ANT-11755']
    active_caregivers = active_caregivers[
        active_caregivers['Caregiver Code - Office'].isin(problematic_codes)].reset_index()

    # Get Notification Method ID for each caregiver
    notifications_dict = await get_notification_methods()
    notifications_dict['Voice Mail'] = notifications_dict['Voice Message']
    active_caregivers['Notification ID'] = [notifications_dict[active_caregivers['Preferred Contact Method'][i]] if
                                            pd.notna(active_caregivers.loc[i, 'Preferred Contact Method']) else "" for i
                                            in
                                            range(len(active_caregivers))]

    df_notes = pd.read_csv(
        "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\Caregiver Notes.csv")
    df_notes['Date'] = pd.to_datetime(df_notes['Date'])
    df_notes = df_notes.rename(columns={'Date': 'Discipline Date'})

    df_final = pd.read_csv(
        "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\Disciplinary Final.csv")
    new_final = df_notes[df_notes['Subject'] == 'Disciplinary Final'][['Caregiver Code - Office']].copy()
    new_final.name = 'Caregiver Code - Office'
    df_final = pd.concat([df_final, new_final], ignore_index=True)
    df_final.drop_duplicates(inplace=True)
    csv_file = "C:\\Users\\nochum.paltiel\\OneDrive - Anchor Home Health care\\Documents\\Caregiver Team Report\\Disciplinary Final.csv"
    df_final.to_csv(csv_file, index=False)

    # Define the conditions and choices for Discipline Expiry Date
    conditions = [
        df_notes['Subject'] == 'Disciplinary Action',
        df_notes['Subject'] == 'Disciplinary Verbal',
        df_notes['Subject'] == 'Disciplinary Written 1',
        df_notes['Subject'] == 'Disciplinary Written 2'
    ]

    # Define the number of days to add based on the conditions
    choices = [
        df_notes['Discipline Date'] + pd.Timedelta(days=30),
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
    latest_expiry = df_notes.loc[idx, ['Caregiver Code - Office', 'Discipline Date', 'Expiry Date']].reset_index(
        drop=True)
    latest_expiry['Expiry Date'] = pd.to_datetime(latest_expiry['Expiry Date']).dt.date

    active_caregivers = pd.merge(active_caregivers, latest_expiry, on='Caregiver Code - Office',
                                 how='left')
    active_caregivers['Disciplinary'] = np.where(
        (~active_caregivers['Caregiver Code - Office'].isin(df_final['Caregiver Code - Office']))
        &
        ((
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
         )),
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
    # back_to_1 = active_caregivers[
    #     (active_caregivers['Team'] == 'Tier 2') &
    #     (active_caregivers['Disciplinary'] == False) &
    #     (~active_caregivers['Caregiver Code - Office'].isin(df_final['Caregiver Code - Office']))
    #     ].copy().reset_index(drop=True)

    back_to_1 = active_caregivers

    make_tier1 = pd.concat([make_tier1, back_to_1], ignore_index=True)

    prob_dict = make_probation.to_dict(orient='index')
    tier1_dict = make_tier1.to_dict(orient='index')
    tier2_dict = make_tier2.to_dict(orient='index')

    teams_dict = await get_teams()
    # Gather async tasks for team updates

    results = await asyncio.gather(
        *(update_team(prob_dict[caregiver], teams_dict['Probation']) for caregiver in prob_dict),
        *(update_team(tier1_dict[caregiver], teams_dict['Tier 1']) for caregiver in tier1_dict),
        *(update_team(tier2_dict[caregiver], teams_dict['Tier 2']) for caregiver in tier2_dict)
    )

    retry_caregivers = [caregiver_code for caregiver_code, success, error_message in results if
                        not success]
    retry_prob = {
        key: details for key, details in prob_dict.items()
        if details.get('Caregiver Code - Office') in retry_caregivers
    }
    retry_tier1 = {
        key: details for key, details in tier1_dict.items()
        if details.get('Caregiver Code - Office') in retry_caregivers
    }
    retry_tier2 = {
        key: details for key, details in tier2_dict.items()
        if details.get('Caregiver Code - Office') in retry_caregivers
    }

    results2 = await asyncio.gather(
        *(update_team(retry_prob[caregiver], teams_dict['Probation']) for caregiver in retry_prob),
        *(update_team(retry_tier1[caregiver], teams_dict['Tier 1']) for caregiver in retry_tier1),
        *(update_team(retry_tier2[caregiver], teams_dict['Tier 2']) for caregiver in retry_tier2)
    )

    # Count successes and collect failure codes
    first_success_count = sum(1 for _, success, _ in results if success)
    second_success_count = sum(1 for _, success, _ in results2 if success)
    failed_caregivers = [(caregiver_code, error_message) for caregiver_code, success, error_message in results2 if
                         not success]

    # Output results
    print(f"Initial successes: {first_success_count}")
    print(f"Secondary successes: {second_success_count}")
    print(f"Total failures: {len(failed_caregivers)}")
    print("Failed Caregiver Codes and Error Messages:")

    for caregiver_code, error_message in failed_caregivers:
        print(f"Caregiver Code: {caregiver_code}, Error: {error_message}")


# Run the asynchronous main function
asyncio.run(main())
