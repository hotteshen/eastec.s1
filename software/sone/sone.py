from typing import Callable, List

from fastapi import HTTPException

from .models import Status, Schedule, Program
from .singletone import Singleton
from .utils import get_sauna_id, get_sauna_id_qr, get_sauna_name, get_default_status


class SOne(Singleton):

    sauna_id: str = get_sauna_id()
    sauna_id_qr: str = get_sauna_id_qr()
    model_name: str = get_sauna_name()
    status: Status = get_default_status()
    schedules: List[Schedule] = []
    program: Program = None

    kfive_update: Callable = lambda x: x

    def set_state(self, state: str) -> Status:
        if state not in ['standby', 'heating', 'ready', 'insession', 'paused']:
            raise HTTPException(
                status_code=422,
                detail="Sauna state must be one of 'standby', 'playing', and 'paused'")
        self.status.state = state
        self.kfive_update(self.status)
        return self.status

    def set_timer(self, timer: int) -> Status:
        if timer > 90 or timer < 0:
            raise HTTPException(
                status_code=422,
                detail="Sauna timer value should be between 0 and 90")
        self.status.timer = timer
        self.kfive_update(self.status)
        return self.status

    def set_target_temperature(self, temperature: int) -> Status:
        if temperature > 70 or temperature < 20:
            raise HTTPException(
                status_code=422,
                detail="Sauna temperature value should be between 20 and 70")
        self.status.target_temperature = temperature
        self.kfive_update(self.status)
        return self.status

    def set_heaters(self) -> Status:
        raise Exception("Not implemented yet")

    def set_lights(self) -> Status:
        raise Exception("Not implemented yet")

    def set_program(self, program: Program) -> Status:
        self.program = program
        self.set_timer(program.timer_duration)
        self.set_target_temperature(program.target_temperature)
        # self.set_lights(program.lights)
        # self.set_heaters(program.heaters)
        return self.status
