def processCriteriaCorrections(correction_parts):
    correction_columns = {}
    correction_columns["Boxscore/Scoresheet"] = "Boxscore"
    correction_columns['Team'] = ""
    correction_columns['Type'] = "Criteria"
    
    if (len(correction_parts) == 1 or len(correction_parts) == 2):
        correction_columns['Category'] = ""
    elif (len(correction_parts) == 3): 
        correction_columns['Category'] = correction_parts[1]

    return correction_columns

def processInsertions():

def processDeletions():

def processMovements():

def processEditions():

def processInvalidCorrections():

def processScoresheetCorrections():

points = ['2P', 'Two Pointer', '3P', 'Three Pointer', 'FTM', 'Free Thrown In'] 
fouls = ['OF FOUL', 'Offensive Foul', 'FOUL', 'Foul', 'UF', 'Unsportsmanlike Foul', 'TECH', 'Technical Foul', 'DQ Foul', 'Disqualifying Foul']
jump_ball = ['Jump Ball']
team_timeouts = ['TOUT', 'Time Out']
irs = ['IRS', 'Instant Replay'] 
coach_challenge = ['CC', 'Coach Challenge']
substitutions = ['In', 'Out']
missed_shots = ['M2P', 'Missed Two Pointer', 'M3P', 'Missed Three Pointer', 'MFT', 'Missed Free Throw']
shots = missed_shots + points

scoresheet_lists = points + fouls + jump_ball + team_timeouts + irs + coach_challenge + substitutions + shots

category_list = [
                    "3P", "2P", "AS", "BLK", "CC", "DR", "DQ FOUL", 
                    "FB", "FD", "FOUL", "FTM", "IRS", "JB", "MFT",
                    "M3P", "M2P", "OF FOUL", "OR", "PF", "REB", "SR",
                    "ST", "SUBS", "TECH", "TOUT", "TO", "UF"
                ]