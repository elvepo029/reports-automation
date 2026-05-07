from dataclasses import dataclass

@dataclass
class Correction:
    game_code: str = ""
    time: str = ""
    quarter: str = ""
    points_h: str = ""
    points_a: str = ""
    action_num: str = ""
    b_ss: str = ""
    team: str = ""     
    type_c: str = ""
    category: str = ""
    thread_name: str = ""
    correction: str = ""