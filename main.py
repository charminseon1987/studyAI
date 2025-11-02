import requests


url = "https://weworkremotely.com/categories/remote-full-stack-programming-jobs"

response = requests.get(url)
print(response.status_code)
# print(response.content)
# print(response.text[:500])
from bs4 import BeautifulSoup


soup = BeautifulSoup(response.content, "html.parser")
jobs = soup.find("section", id="category-2").find_all("li")[1:-1]
print(jobs)
print(len(jobs))
for job in jobs:
    
    title = job.find("h3",class_="new-listing__header__title").text
    company = job.find("p", class_="new-listing__company-name").text
    #  time,salary,region
    a = job.find_all("p",class_="new-listing__categories__category")
    if len(a) == 3: 
        # print(f"3개일경우 : {a}")
        time,income, region = a
        time = a[0].text
        income = a[1].text 
        region = a[2].text 
        print(f"3개일경우 : time:{time},income: {income}, region:{region}")

    elif len(a) == 2: 
        # print(f"2개일 경우:  {a}")
        time,region= a
        time = a[0].text 
        region = a[1].text 
        print(f"2개일 경우: time:{time},region:{region}")
    else: 
        print(f"{len(a)}")
    # print(f"Job_title: {title}, company : {company},region:{region}")
#     print(f"'a':{a}")

    # print(f"{title}, '------',{company}")