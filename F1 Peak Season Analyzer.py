import fastf1
from fastf1.ergast import Ergast
import pandas as pd
import numpy as np

Seasons = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
'''Cache_Dir = 'cache'

fastf1.Cache.enable_cache(Cache_Dir)'''
ergast = Ergast()

Overrides = {
    "zhou guanyu": "ZHO",
    "guanyu zhou": "ZHO",
    "kimi raikkonen": "RAI",
    "kimi räikkönen": "RAI",
}



def name_getter(driver_name):
    driver_name = driver_name.strip().lower()
    if driver_name in Overrides:
        return Overrides[driver_name]

    last_name = driver_name.split()[-1]
    name = last_name[0:3].upper()
    return name



def prompt_driver_code():
    driver_name = input("What is the name of the driver you would like to analyze? (First Last): ")
    print(name_getter(driver_name))

    correct_Code = input("Is this correct? Input Y/N:")
    if correct_Code.upper() == "N":
        last_name = input("Please input the correct code: ")
        name = last_name[0:3].strip().upper()
        return name
    else:
        return name

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def compute_tire_degradation(laps):

    #Essentially, for each stint, lap time is plotted as the y-axis and lap number is plotted as the x-axis. A linear regression is then performed on the data, and the slope of the line is returned. The slope represents the rate of tire degradation for that stint. If the slope is small, then the lap times aren't changing much, so it's good tire management. If the slope is large, then the lap times are increasing quickly, so it's bad tire management. 

    slopes = []
    for specific_stint in laps['Stint'].unique(): #looks at each unique stint in the laps dataframe
        stint = laps[laps['Stint'] == specific_stint].copy() #filters down to just this stints laps and makes a copy of the dataframe to avoid SettingWithCopyWarning
        stint = stint[stint["PitInTime"].isna() & stint["PitOutTime"].isna()] #filters out laps that have pit in or pit out times, as these are not representative of the tire degradation for that stint

        stint = stint.dropna(subset=['LapTime', "TyreLife"]) #drops any laps that have NaN values for LapTime or TyreLife, as these are not representative of the tire degradation for that stint
        if len(stint) < 4: #len -> number of rows in the dataframe. If there are less than 4 laps in the stint, then it's not enough data to perform a linear regression, so we skip this stint.
            continue

        lap_times = stint['LapTime'].dt.total_seconds().values #converts the LapTime column to total seconds (as a number) and gets the values as a numpy array
        tyre_life = stint['TyreLife'].values #gets the TyreLife column as a numpy array

        z = np.abs((lap_times - lap_times.mean()) / (lap_times.std() + 1e-9)) #drops obvious outlier laps (safety cars, traffic, etc.) by calculating the z-score of each lap time and filtering out any laps that are more than 3 standard deviations away from the mean. The 1e-9 is added to the standard deviation to avoid division by zero in case all lap times are the same.
        #abs means the deviation is always positive

        mask = z < 2 #creates a boolean mask where True means the lap time is within 2 standard deviations of the mean, and False means the lap time is an outlier
        if mask.sum() < 4: #counts how many True values are in mask
            continue

        slope, 
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def analyze_season(year, driver_code):
    schedule = fastf1.get_event_schedule(year)
    race_rounds = schedule[schedule['EventFormat'] != 'testing']['RoundNumber'].tolist() #Schedule is a 2-D array, and RoundNumber is where the round number is held. It is then converted to list

    tire_slopes = [] #creates an empty list to hold the tire slopes for each race in the season
    wet_deltas = [] #creates an empty list to hold the wet deltas for each race in the season
    dry_deltas = [] #creates an empty list to hold the dry deltas for each race in the season
    finish_gaps = [] #creates an empty list to hold the finish gaps for each race in the season

    team_change = set() #creates a set to hold all the teams the driver has been on in that season

    rank_cache = {} # Dictionary to cache the rank of each team the driver has been on in that season

    for round in race_rounds:
        try:
            race = fastf1.get_session(year, round, 'R')
            race.load()
            driver_data = race.laps.pick_driver(driver_code)

        except Exception:
            continue #skips races with no data at all

        result = race.results[race.results['Abbreviation'] == driver_code]
        if result.empty:
            continue #skips races where the driver did not participate

        team_name = result.iloc[0]['TeamName'] #finds team name of the driver for that race by taking the first row (0) of the result dataframe and accessing the 'TeamName' column
        team_change.add(team_name) #adds the team name to the set of all teams for that driver in that season

        if team_name not in rank_cache: 
            try:
                rank_cache[team_name] = get_constructor_rank(year, team_name) #if the team is not already in the rank_cache, it calls get_constructor_rank to get the rank of that team for that season and adds it to the rank_cache
            except Exception:
                rank_cache[team_name] = None #if there is an error getting the rank, it sets the rank to None

        constructor_rank = rank_cache[team_name]

        driver_laps = race.laps.pick_driver(driver_code)
        if driver_laps.empty:
            continue #skips races where the driver did not complete any laps

        if constructor_rank: #looks at car relative results and compares them to the expected finish based on constructor rank
            expected_position = expected_finish(constructor_rank)
            actual_position = result.iloc[0]['Position']
            if pd.notna(actual_position): #pandas method to check if the actual_position is not NaN (not a number). This is important because some races may have missing data for the driver's finish position.
                finish_gaps.append(expected_position - actual_position) #adds the difference between expected and actual finish position to the finish_gaps list. If positive, then overperformed.

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def get_constructor_rank(year, team_name):
    standings = ergast.get_constructor_standings(season=year).content[0]

    team_row = standings[standings['constructorName'].str.contains(team_name.split()[0], case=False, na=False)] #finds the row in the standings dataframe where the constructorName contains the first word of the team_name (case insensitive)
    if team_row.empty:
        return None

    rank = int(team_row.iloc[0]['position']) #in the dataframe, the position column is a string, so it is converted to an integer
    return rank



def expected_finish(rank, grid_size = 20):
    return min(grid_size, max(1, rank * 2 - 1)) #returns the expected finish position based on the constructor rank and grid size. The expected finish is calculated as the grid size or the maximum of 1 and (rank * 2 - 1). This means that if the rank is 1, the expected finish is 1, if the rank is 2, the expected finish is 3, and so on. If the rank is greater than half the grid size, the expected finish will be capped at the grid size.

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def main():
   name = prompt_driver_code()

   records = []
   for year in Seasons:
       try:
           result = analyze_season(year, name)

           if not result["teams"]:
             print(f"No data found for {name} in {year}.")
             continue

           records.append(result)
           print(f"  ->{result}")
       except Exception as e:
           print(f"Error retrieving data for {year}: {e}")

    


if __name__ == "__main__":  # when script is run, call main
    main()