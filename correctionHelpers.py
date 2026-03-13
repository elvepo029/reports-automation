from correction import Correction
import re

def processCriteriaCorrections(action_abb, correction_instruction, home_team, away_team, action_parts, correction_parts) -> Correction:
    b_ss = "BOXSCORE"
    type_c = "CRITERIA"

    team = ""
    category = ""

    if correction_instruction == "insert":
        if len(correction_parts) == 3:
            if correction_parts[1].upper() in category_list:
                category = correction_parts[1]
            else:
                category = ""

            if "A" in correction_parts[2]:
                team = "HOME TEAM"
            elif "B" in correction_parts[2]:
                team = "AWAY TEAM"
            else:
                team = ""

        elif len(correction_parts) == 2:
            stat = correction_parts[1]

            if stat in no_team_actions and stat in category_list:
                team = "NO TEAM"
                category = stat

        else:
            category = ""
            team = ""

    elif correction_instruction == "edit":
        if len(correction_parts) == 2:
            if correction_parts[1].upper() in category_list:
                category = correction_parts[1]
            else:
                category = action_abb

            if "A" in correction_parts[1] and correction_parts[1] not in category_list:
                team = "HOME TEAM"
            elif "B" in correction_parts[1] and correction_parts[1] not in category_list:
                team = "AWAY TEAM"
            else:
                if action_parts[6] == home_team:
                    team = "HOME TEAM"
                elif action_parts[6] == away_team:
                    team = "AWAY TEAM"
                else:
                    team = ""
            
        elif len(correction_parts) == 3:
            if correction_parts[1].upper() in category_list:
                category = correction_parts[1]
            else:
                category = action_abb

            if "A" in correction_parts[2]:
                team = "HOME TEAM"
            elif "B" in correction_parts[2]:
                team = "AWAY TEAM"
            else:
                team = ""

        else:
            category = ""
            team = ""

    elif correction_instruction == "delete" or correction_instruction == "move":
        category = action_abb
        
        if action_parts[6] == home_team:
            team = "HOME TEAM"
        elif action_parts[6] == away_team:
            team = "AWAY TEAM"
        else:
            team = ""

    else:
        category = ""
        team = ""
    
    return Correction(
        b_ss = b_ss,
        team = team,
        type_c = type_c, 
        category = category
    )

def processInsertions(correction_parts) -> Correction:
    type_c = "MISSING"
    b_ss = "BOXSCORE"

    if len(correction_parts) == 3:
        if correction_parts[1].upper() in category_list:
            category = correction_parts[1]
        else:
            category = ""

        if "A" in correction_parts[2]:
            team = "HOME TEAM"
        elif "B" in correction_parts[2]:
            team = "AWAY TEAM"
        else:
            team = ""

    elif len(correction_parts) == 2:
        stat = correction_parts[1]

        if stat in no_team_actions and stat in category_list:
            team = "NO TEAM"
            category = stat
        else:
            team = ""
            category = ""

    else:
        team = ""
        category = ""

    return Correction(
        b_ss = b_ss,
        team = team,
        type_c = type_c,
        category = category
    )

def processDeletions(action_abb, home_team, away_team, action_parts) -> Correction:
    b_ss = "BOXSCORE"
    type_c = "NOT HAPPENED"
    category = action_abb

    if action_parts[6] == home_team:
        team = "HOME TEAM"
    elif action_parts[6] == away_team:
        team = "AWAY TEAM"
    else:
        team = ""

    return Correction(
        b_ss = b_ss,
        team = team,
        type_c = type_c, 
        category = category
    )

def processMovements(action_abb, home_team, away_team, action_parts) -> Correction:
    b_ss = "BOXSCORE"
    type_c = "MISPLACED"
    category = action_abb

    if action_parts[6] == home_team:
        team = "HOME TEAM"
    elif action_parts[6] == away_team:
        team = "AWAY TEAM"
    else:
        team = ""

    return Correction(
        b_ss = b_ss,
        team = team,
        type_c = type_c, 
        category = category
    )

def processEditions(action_abb, home_team, away_team, action_parts, correction_parts) -> Correction:
    b_ss = "BOXSCORE"

    if len(correction_parts) == 2:
        stat = correction_parts[1]

        if stat in category_list:
            category = action_abb
            type_c = "NOT HAPPENED"

            if action_parts[6] == home_team:
                team = "HOME TEAM"
            elif action_parts[6] == away_team:
                team = "AWAY TEAM"
            else:
                team = "NO TEAM"
        
        elif "A" in stat or "B" in stat:
            category = action_abb
            type_c = "MISIDENTITY"

            if "A" in correction_parts[1]:
                team = "HOME TEAM"
            elif "B" in correction_parts[1]:
                team = "AWAY TEAM"
            else:
                team = ""

        else:
            team = ""
            category = ""
            type_c = ""

    elif len(correction_parts) == 3:
        stat = correction_parts[1]

        if stat in category_list:
            category = action_abb
            type_c = "NOT HAPPENED"

            if "A" in correction_parts[2]:
                team = "HOME TEAM"
            elif "B" in correction_parts[2]:
                team = "AWAY TEAM"
            else:
                team = ""

        else:
            team = ""
            category = ""
            type_c = ""

    else:
        team = ""
        type_c = ""
        category = ""

    return Correction(
        b_ss = b_ss,
        category = category,
        type_c = type_c,
        team = team
    )

def processInvalidCorrections() -> Correction:
    return Correction(
        b_ss = "",
        team = "",
        type_c = "", 
        category = ""
    )

def processScoresheetCorrections(action_abb, correction_instruction, home_team, away_team, action_parts, correction_parts) -> Correction:
    b_ss = "SCORESHEET"

    if correction_instruction == "insert":
        if len(correction_parts) == 3:
            stat = correction_parts[1]
            if stat in category_list:
                category = stat
            else:
                category = ""

            if "A" in correction_parts[2]:
                team = "HOME TEAM"
            elif "B" in correction_parts[2]:
                team = "AWAY TEAM"
            else:
                team = ""

        elif len(correction_parts) == 2:
            stat = correction_parts[1]

            if stat in no_team_actions and stat in category_list:
                team = "NO TEAM"
                category = stat
            else:
                team = ""
                category = ""

        else:            
            category = ""
            team = ""

    elif correction_instruction == "edit":
        if len(correction_parts) == 2:
            if "FT" in correction_parts[1]:
                number_ft = int(action_parts[11])
                correction_number_ft = getNumberOfFTFromCorrection(correction_parts[1])

                if correction_number_ft != 4:
                    category = "DSS FREE THROWS"
                    if correction_number_ft > number_ft:
                        type_c = "MISSING"
                    elif correction_number_ft < number_ft:
                        type_c = "NOT HAPPENED"
                    else:
                        type_c = ""

                else:
                    category = correction_parts[1]
            
                if action_parts[6] == home_team:
                    team = "HOME TEAM"
                elif action_parts[6] == away_team:
                    team = "AWAY TEAM"
                else:
                    team = ""

            elif "A" in correction_parts[1] or "B" in correction_parts[1]:
                category = action_abb
                correction_parts_1 = correction_parts[1]

                if "A" in correction_parts_1 and correction_parts_1 not in category_list:
                    team = "HOME TEAM"
                elif "B" in correction_parts_1 and correction_parts_1 not in category_list:
                    team = "AWAY TEAM"
                else:
                    if action_parts[6] == home_team:
                        team = "HOME TEAM"
                    elif action_parts[6] == away_team:
                        team = "AWAY TEAM"
                    else:
                        team = ""

            else:
                category = ""
                team = ""

        else:
            category = ""
            team = ""

    elif correction_instruction == "delete" or correction_instruction == "move":
        category = action_abb
        
        if action_parts[6] == home_team:
            team = "HOME TEAM"
        elif action_parts[6] == away_team:
            team = "AWAY TEAM"
        else:
            team = ""

    if category in shots:
        type_c = "POINTS"
    elif category in fouls:
        type_c = "FOULS"
    elif category in jump_ball:
        type_c = "JUMP BALL"
    elif category in team_timeouts:
        type_c = "TIME OUTS"
    elif category in irs:
        type_c = "INSTANT REPLAY"
    elif category in coach_challenge:
        type_c = "COACH CHALLENGE"
    elif category in substitutions:
        type_c = "SUBSTITUTIONS"
    elif category == "DSS FREE THROWS":
        type_c = type_c
    else:
        type_c = ""

    return Correction(
        b_ss = b_ss,
        team = team,
        type_c = type_c,
        category = category
    )

def processTimingCorrections(action_abb, home_team, away_team, action_parts, correction_parts) -> Correction:
    b_ss = "BOXSCORE"
    type_c = "TIMING"
    category = action_abb

    if action_parts[6] == home_team:
        team = "HOME TEAM"
    elif action_parts[6] == away_team:
        team = "AWAY TEAM"
    else:
        team = ""

    if len(correction_parts) == 2:
        time = correction_parts[1]
    else:
        time = ""

    return Correction(
        time = time,
        b_ss = b_ss,
        team = team,
        type_c = type_c, 
        category = category
    )

points = ['2P', 'Two Pointer', '3P', 'Three Pointer', 'FTM', 'Free Thrown In'] 
fouls = ['OF FOUL', 'Offensive Foul', 'FOUL', 'Foul', 'UF', 'Unsportsmanlike Foul', 'TECH', 'Tech Foul', 'TECH COACH', 'Tech Foul Coach', 'TECH BENCH', 'Tech Foul Bench', 'DQ Foul', 'Disqualifying Foul']
jump_ball = ['Jump Ball', 'JB']
team_timeouts = ['TOUT', 'Time Out']
irs = ['IRS', 'Instant Replay'] 
coach_challenge = ['CC', 'Coach Challenge']
substitutions = ['IN', 'In', 'OUT', 'Out']
missed_shots = ['M2P', 'Missed Two Pointer', 'M3P', 'Missed Three Pointer', 'MFT', 'Missed Free Throw']
shots = missed_shots + points

scoresheet_lists = points + fouls + jump_ball + team_timeouts + irs + coach_challenge + substitutions + shots

category_list = [
                    "3P", "2P", "AS", "BLK", "CC", "DR", "DQ_FOUL", 
                    "FD", "FOUL", "FTM", "IRS", "JB", "MFT",
                    "M3P", "M2P", "OF_FOUL", "OR", "SR",
                    "ST", "IN", "OUT", "TECH", "TOUT", "TO", "UF",
                    "TV_TOUT", "TI_FOUL", "TECH_COACH", "TECH_BENCH"
                ]

no_team_actions = ['IRS', 'Instant Replay', 'TV_TOUT', 'TV Time Out', 'JB', 'Jump Ball', 'BQ', 'Begin Quarter', 'EQ', 'End Quarter']

def getNumberOfFTFromCorrection(value: str) -> int:
    if re.fullmatch(r"[1-3]FT", value):
        return int(value[0])
    return 4