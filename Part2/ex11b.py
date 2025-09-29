def calculate(number1, operator, number2):
    if operator == "+":
        return number1 + number2
    elif operator == "-":
        return number1 - number2
    elif operator == "*":
        return number1 * number2
    elif operator == "/":
        return number1 / number2
print(calculate(2, "+", 2))
print(calculate(2, "-", 2))
print(calculate(2, "*", 2))
print(calculate(2, "/", 2))