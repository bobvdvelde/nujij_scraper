# NuJij.nl scraper

## why?

We want to save this dutch news-forum for posterity

## how? 

Python!

go to where you've cloned this repo. 

```bash
# you probably want to do this in a virtualenvironment!
cd this_repo
pip install -r Requirements
python nujij_scraper.py

```
OR you go all **21st century** and jump on the **containerized micro-services bandwagon**

```bash
cd <directory_you_want_full_of_json>
docker run -v "$(pwd)":/json rnvdv/nujij ipython /home/nujij_scraper.py
```

*nice*


