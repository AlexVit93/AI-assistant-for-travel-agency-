from aiogram.fsm.state import State, StatesGroup

class StateGpt(StatesGroup):
  text = State()
  greeted = State()
  waiting_for_query = State()
  getting_contact = State()