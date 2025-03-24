from fastapi import FastAPI
from pydantic import BaseModel
import math

app = FastAPI()

sports = ["Football", "Basketball", "Tennis", "Swimming", "Golf"]
caloric_burn_rates = {"Football": 5, "Basketball": 12, "Tennis": 8, "Swimming": 1, "Golf": 5}
cals = [250, 500, 1000]

class UserInput(BaseModel):
    gender: str
    weight: float
    height: float
    age: int
    activity_level: str
    sport: list[str]
    aantal_minuten_sporten: int
    gewenst_gewicht: float
    deficit_surplus: int

def calculate_time(sport, weight, gewenst_gewicht, time, deficit_surplus):
    if gewenst_gewicht > weight:
        total = deficit_surplus
        return (7000 * abs(weight - gewenst_gewicht)) / abs(total)
    else:
        total = 0
        for x in caloric_burn_rates:
            if sport == x:
                total = caloric_burn_rates[x] * time
        if weight > gewenst_gewicht:
            total += deficit_surplus
        else:
            total -= deficit_surplus
        return (7000 * abs(weight - gewenst_gewicht)) / abs(total)

def calculate_bmr(weight, height, age, gender):
    if gender.lower() == "male":
        return (10 * weight) + (6.25 * height) - (10 * age) + 5
    elif gender.lower() == "female":
        return (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        raise ValueError("Invalid gender input. Use 'male' or 'female'.")

def calculate_tdee(bmr, activity_level):
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9
    }
    return bmr * activity_multipliers.get(activity_level, 1.2)

@app.post("/calculate")
def calculate(input_data: UserInput):
    BMR = calculate_bmr(input_data.weight, input_data.height, input_data.age, input_data.gender)
    TDEE = calculate_tdee(BMR, input_data.activity_level)

    results = []
    for i in cals:
        for v in input_data.sport:
            tijd = calculate_time(v, input_data.weight, input_data.gewenst_gewicht, input_data.aantal_minuten_sporten, i)
            if input_data.gewenst_gewicht > input_data.weight:
                results.append({
                    "TDEE": round(TDEE, 2),
                    "goal": round(TDEE + i, 2),
                    "time_to_reach_goal": round(tijd, 2),
                })
            else:
                results.append({
                    "TDEE": round(TDEE, 2),
                    "goal": round(TDEE - i, 2),
                    "time_to_reach_goal": round(tijd, 2),
                })

    return {"results": results}
