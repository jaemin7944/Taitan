import undetected_chromedriver as uc

url = "https://www.stocktitan.net/news/trending.html"

options = uc.ChromeOptions()
options.add_argument("--headless=new")

driver = uc.Chrome(options=options)

driver.get(url)

print(driver.title)
print(driver.page_source[:500])

driver.quit()
