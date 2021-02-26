from selenium import webdriver
import time

driver = webdriver.Firefox(executable_path='c:/program/geckodriver.exe')

URL = "https://www.quora.com/What-is-the-best-workout-1"
driver.get(URL)



PAUSE_TIME = 2


lh = driver.execute_script("return document.body.scrollHeight")

while True:

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(PAUSE_TIME)
    nh = driver.execute_script("return document.body.scrollHeight")
    if nh == lh:
        break
    lh = nh
spans = driver.find_elements_by_css_selector('span.q-box.qu-userSelect--text')
for span in spans:
    print(span.text)
    print('-' * 80)
