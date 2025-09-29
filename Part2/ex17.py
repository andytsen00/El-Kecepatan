print("What is your name?")
user_name = input()

import random
adjectives = ["Cheerful", "Gentle", "Curious", "Brave", "Playful", "Patient"]
animals = ["Pangolin", "Axolotl", "Okapi", "Fossa", "Quokka", "Kakapo"]
print(f"{user_name}, your codename is: {random.choice(adjectives)} {random.choice(animals)}")
print(f"Your lucky number is: {random.randint(1,99)}")