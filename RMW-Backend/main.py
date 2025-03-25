from fastapi import FastAPI, HTTPException
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
    """
    Calculate time to reach goal weight
    
    Args:
        sport: Type of sport
        weight: Current weight in kg
        gewenst_gewicht: Goal weight in kg
        time: Minutes of sport per day
        deficit_surplus: Caloric deficit or surplus
        
    Returns:
        Estimated days to reach goal
    """
    # Avoid division by zero
    if deficit_surplus == 0 and (sport not in caloric_burn_rates or time == 0):
        return float('inf')  # Infinite time if no caloric changes
    
    if gewenst_gewicht > weight:
        # Weight gain scenario
        total = deficit_surplus
        if total <= 0:
            return float('inf')  # Can't gain weight with deficit
        return (7000 * abs(weight - gewenst_gewicht)) / abs(total)
    else:
        # Weight loss scenario
        total = 0
        for x in caloric_burn_rates:
            if sport == x:
                total = caloric_burn_rates[x] * time
        
        # Add deficit for weight loss
        if weight > gewenst_gewicht:
            total += deficit_surplus
        else:
            total -= deficit_surplus
            
        # Can't lose weight without caloric deficit
        if total <= 0:
            return float('inf')
            
        return (7000 * abs(weight - gewenst_gewicht)) / abs(total)

def calculate_bmr(weight, height, age, gender):
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation
    
    Args:
        weight: Weight in kg
        height: Height in cm
        age: Age in years
        gender: 'male' or 'female'
        
    Returns:
        BMR in calories per day
    """
    if gender.lower() == "male":
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender.lower() == "female":
        return (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        # Default to male formula if gender is not recognized
        return (10 * weight) + (6.25 * height) - (5 * age) + 5

def calculate_tdee(bmr, activity_level):
    """
    Calculate Total Daily Energy Expenditure
    
    Args:
        bmr: Basal Metabolic Rate
        activity_level: One of 'sedentary', 'light', 'moderate', 'active', 'very active'
        
    Returns:
        TDEE in calories per day
    """
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9
    }
    
    # Convert to lowercase and get multiplier (default to sedentary if not found)
    activity_level = activity_level.lower()
    multiplier = activity_multipliers.get(activity_level, 1.2)
    
    return bmr * multiplier

@app.post("/calculate")
def calculate(input_data: UserInput):
    """
    Calculate time to reach goal weight based on input data
    
    Args:
        input_data: User input data including current stats and goals
        
    Returns:
        Dictionary with calculation results
    """
    try:
        # Validate input
        if not input_data.sport:
            raise HTTPException(status_code=400, detail="At least one sport must be selected")
            
        # Calculate BMR and TDEE
        BMR = calculate_bmr(input_data.weight, input_data.height, input_data.age, input_data.gender)
        TDEE = calculate_tdee(BMR, input_data.activity_level)
        
        # Calculate the days to goal (average of all calculations)
        days_total = 0
        count = 0
        valid_calculations = 0
        
        results = []
        for i in cals:
            for v in input_data.sport:
                try:
                    # Skip invalid sports
                    if v not in caloric_burn_rates:
                        continue
                        
                    tijd = calculate_time(v, input_data.weight, input_data.gewenst_gewicht, input_data.aantal_minuten_sporten, i)
                    
                    # Skip infinite time results
                    if not math.isinf(tijd):
                        days_total += tijd
                        valid_calculations += 1
                    
                    count += 1
                    
                    if input_data.gewenst_gewicht > input_data.weight:
                        # Weight gain
                        results.append({
                            "sport": v,
                            "calorie_adjustment": i,
                            "TDEE": round(TDEE, 2),
                            "goal": round(TDEE + i, 2),
                            "time_to_reach_goal": round(tijd, 2),
                        })
                    else:
                        # Weight loss
                        results.append({
                            "sport": v,
                            "calorie_adjustment": i,
                            "TDEE": round(TDEE, 2),
                            "goal": round(TDEE - i, 2),
                            "time_to_reach_goal": round(tijd, 2),
                        })
                except Exception as e:
                    print(f"Error calculating for sport {v} with deficit {i}: {str(e)}")
        
        # Calculate average days to goal (only from valid calculations)
        if valid_calculations > 0:
            days_to_goal = days_total / valid_calculations
        else:
            days_to_goal = float('inf')
            
        # If days to goal is infinite, set a very high number
        if math.isinf(days_to_goal):
            days_to_goal = 9999
        
        return {
            "results": results,
            "days_to_goal": round(days_to_goal, 2),
            "BMR": round(BMR, 2),
            "TDEE": round(TDEE, 2),
            "weight_difference": round(abs(input_data.weight - input_data.gewenst_gewicht), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in calculation: {str(e)}")