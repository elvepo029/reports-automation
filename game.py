from dataclasses import dataclass

@dataclass
class Game:
    game_code: str = ""
    code_h: str = ""
    code_a: str = ""
    year: int = 0
    month: int = 0
    day: int = 0
    round: int = 0
    data_entry: str = ""     
    caller_1: str = ""
    caller_2: str = ""
    timer: str = ""
    shot_clock_operator: str = ""
    irs_operator: str = ""
    is_processed: bool = False
    arrival_time: str = ""
    checklist_on_time: str = ""
    communication: str = ""
    corrections_speed: str = ""
    rescouted: str = ""
    total_actions: int = 0
    total_corrections: int = 0
    lgm_comment: str = ""
    result: float = 0.0