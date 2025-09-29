age = {"Hans" : 24, "Prag" : 23, "Bunyod" : 18}
print(age)
print(age["Hans"])
age.update({"Prag" : 30})
print(age["Prag"])
del age["Bunyod"]
print(age)