# todo_list=[]

# todo_list.append('강의듣기')
# todo_list.append('영화보기')
# todo_list.append('청소하기')

# print(todo_list)


# for i, task in enumerate(todo_list,1):
#     print(f"{i}:{task}")
# todo_list.remove("영화보기")
# print(todo_list)

# person = {
#     "name": "hyeseon",
#     "age" : 30
# }
# print(person["name"])
# print(person.get("age"))
# print(person.get("phone","핸드폰 없음"))

# for key ,value in person.items():
#     print(f"{key} : {value}")


students = {
    "김철수" : {"국아": 85 , "영어": 90, "수학": 88},
    "이영희" : {"국아": 92 , "영어": 88, "수학": 95},
    "박민수" : {"국아": 78 , "영어": 85, "수학": 82},
}

# print(sum((40,2)))
# print(len(students))


for name, scores in students.items():
    
    print(scores.values())
    average = sum(scores.values())/len(scores)
    print(f"{name}의 평균 점수는 {average:.2f}입니다.")

#tuple 변경이 불가능한 리스트 
korea=("서울","부산","대구","인천","광주","대전","울산","세종")



