# For url grabbing
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from ratelimit import limits, sleep_and_retry

# For url parsing and scraping
from bs4 import BeautifulSoup
import re
import sys

# Workers and multiprocessing
import multiprocessing as mp
from functools import partial
from contextlib import contextmanager

# Output handeling file
import writer as out


glob_url = 'https://imdb.com/'
ignore_profit = False
class TargetGender:
    def __init__(self, let):
        self.gender = let
    def opposite_gender(self):
        if self.gender == 'm':
            return 'f'
        else:
            return 'm'

target_gender = None

@sleep_and_retry
@limits(calls = 4, period=10)
def simple_get(url):
    # Gets info at a url
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None
    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        sys.exit()
        return None

def is_good_response(resp):
    # Ensures the GET response is good
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
        and content_type is not None
        and content_type.find('html') > -1)

def log_error(e):
    print(e)

def manip_movie(url, actor):
    # We want to return none if the movie does not meet our standards
    # 1: The actor needs to be billed as one of the leading actors
    # 2: The actor needs a female counterpart
    # 3: The movie needs to be considered a 'hit'
    # If the movie meets those requirements, return the actress's name,
    #   and age when the movie was made (year - year)
    # If the movie does not meet those requirements, return none
    html = simple_get(url[0])
    soup = BeautifulSoup(html, 'html.parser')
    actor, gender = actor
    target_gender = TargetGender(gender)

    # 1:
    lead_list = []
    lead_age = 0
    movie_page = soup.find('table', {'class': 'cast_list'})
    leads = movie_page.findAll('tr', {'class': re.compile('odd|even')})
    # This checks to see if the actor is even in the actor list

    actor_is_lead = False
    #for x in range(len(leads)):
    acts_to_grab = 15
    for x in range(acts_to_grab):
        #print(leads[x].td.a.img['alt'])
        try:
            if leads[x].td.a.img['alt'] == actor:
                actor_is_lead = True
        except IndexError:
            print("Actor with no url in parse (scrape.py, 71)")
            print("Movie: " + url[1])
            # Ignore and keep going
            continue
        except AttributeError:
            continue

        lead_list.append({'lead':leads[x].td.a.img['alt'],
                          'lead_url':leads[x].td.a['href'][1:16],
                          'gender':'',
                          'movie':url[1],
                          'age_at_release':None,
                          'movie_year_released':-1,
                          'gpr_hit':False,
                          'net_hit':False,
                          'bad_box':False})


    if actor_is_lead == False: # If the actor we are looking at is not top billed
        return (None, url[1])

    # 2: The actor needs a female counterpart
    try:
        movie_release_year = int(soup.find('span', {'id' : 'titleYear'}).text[1:5])
    except AttributeError:
        #print("==> Attribute Error with movie " + url[1])
        #print("==> This movie has no listed year and has been thrown out of the dataset (scrape.py, 92)")
        #return (None, url[1])
        movie_release_year = soup.find('div', {'class': 'subtext'}).contents[15].text
        movie_release_year = int(re.search(r"(\d{4})", movie_release_year).group(1))

    for l in lead_list:
        l['movie_year_released'] = movie_release_year
        # Check if any of the leads are female. Otherwise, return None
        act_html = simple_get(glob_url + l['lead_url'])
        act_soup = BeautifulSoup(act_html, 'html.parser')
        if target_gender.gender == 'm':
            act_gender = act_soup.find('a', {'href':'#actor'}) # If the actor tag is not present, then they are an actress.
        else:
            act_gender = act_soup.find('a', {'href':'#actress'}) # If the actor tag is not present, then they are an actress.

        # Skip dudes
        if act_gender is not None:
            l['gender'] = target_gender.gender
        else:
            l['gender'] = target_gender.opposite_gender()

        # get the actor's age during the filiming

        actor_birth_year = act_soup.find('time')
        try:
            actor_age_at_release = movie_release_year - int(actor_birth_year.findChildren()[1].text.strip())
            l['age_at_release'] = actor_age_at_release
        except AttributeError:
            print("==> Attribute Error with information from the movie: '" + str(url[1]) + "' with actor " + l['lead'])
            print("==> This actor has been thrown out of the dataset (scrape.py, 121)")
            # Do not add this actors age to the list, becuase IMDB does not have their age listed.
        except IndexError:
            print("==> Index Error with information from the movie: '" + str(url[1]) + "' with actor " + l['lead'])
            print("==> This actor has been thrown out of the dataset (scrape.py, 125)")
            # Do not add this actors age to the list, becuase IMDB does not have their age listed.



    # Trim the list (again) to remove any other male stars:
    for x in range(len(lead_list)):
        if lead_list[x]['gender'] == target_gender.gender and lead_list[x]['lead'] != actor:
            lead_list[x] = None # Nullify the actor, so they will be filtered out later.

    #return True

    # For now, if the lead is the only on in the list, return none for that movie.
    good_loc = -1
    none_count = 0
    for l in lead_list:
        if l is None:
            none_count += 1

    if len(lead_list) - none_count == 1:
        return (None, url[1])

    # 3: The movie needs to be considered a 'hit'
    # This one is more complex. We can do it based off of net gross or IMDB/Metacritic ratings, both work.
    lead_list = greatist_hits(lead_list, soup)

    return lead_list

def greatist_hits(leads, soup):
    # We need to check two numbers:
    # The movie's Gross Revenue Profit (value from -inf to +inf, zero is broke even)
    # The movie's Net Profit (value from -inf to +inf, probably will be in millions)
    # Caclulate both, and mark the both on the list

    # First, grab the name of the movie for debugging:
    movie_title = None
    for l in leads:
        try:
            movie_title = l['movie']
        except:
            continue

    try:
        movie_rev_soup = soup.find('h3', string="Box Office").findNext('div')
    except AttributeError:
        print("====> Movie '" + movie_title + "' does not have a box office listing")
        print("====> This movie will remain undetermined for hit status")
        return leads
    #print("Movie: " + leads[0]['movie'])
    #print(movie_rev_soup.contents[1].string + " " + movie_rev_soup.contents[2].strip())


    # So, we can get one of three div strings each time, those being:
    # Budget, Gross USA, and Cumulative Worldwide Gross
    # so, loop through those and attach the correct values to each
    # If a value is not present, do not assign it and worry about it later.
    gross_str = None
    budget_str = None

    for x in range(5):
        for y in range(len(movie_rev_soup)):
            try:
                if movie_rev_soup.contents[y].string.strip() == "Budget:":
                    #print("MOVIE " + leads[0]['movie'] + " Has BUDGET: " + movie_rev_soup.contents[y + 1].string.strip())
                    budget_str = movie_rev_soup.contents[y + 1].string.strip()
                elif movie_rev_soup.contents[y].string.strip() == "Gross USA:":
                    #print("MOVIE " + leads[0]['movie'] + " Has GROSS: " + movie_rev_soup.contents[y + 1].string.strip())
                    gross_str = movie_rev_soup.contents[y + 1].string.strip()
            except IndexError:
                continue
            except AttributeError:
                continue
            continue

        if movie_rev_soup['class'] == 'see-more inline':
            break

        movie_rev_soup = movie_rev_soup.findNext('div')


    try: # TODO: make this not so much garbage (probably a regex replace or something)
        gross = int(re.sub(r'[^0-9]', '', gross_str))
        budget = int(re.sub(r'[^0-9]', '', budget_str))
        #gross = float(re.sub(r'[^A-Za-z0-9_\.]', '', gross_str)) # Redone, as the previous regex was removing decimal places.
        #budget = float(re.sub(r'[^A-Za-z0-9_\.]', '', budget_str))
        #print("Gross: " + str(gross) + ", Budget: " + str(budget) + ", for movie " + movie_title)
    except AttributeError:
        print("====> Movie '" + movie_title + "' has either no gross or budget")
        return leads
    except TypeError:
        print("====> Movie '" + movie_title + "' has either no gross or budget")
        return leads

    # Cacculate Gross Profit margin (gross - budget)/gross
    gpr = (gross - budget)/gross
    #print("GPR for " + movie_title + " is " + str(gpr))

    # Net Profit
    net_profit = gross - budget
    #print("NET PROFIT for " + movie_title + " is " +str(net_profit))

    # Determing if either of those are above the threshhold for being considered a 'hit'
    # We can either return the entire gpr and net values or we can return true/false if they pass a threshold.
    for l in leads:
        try:
            if ignore_profit is True:
                #l['grp_hit'] = True
                l['gpr_hit'], l['net_hit'] = True, True
                #l['net_hit'] = True
                continue
            if gpr > 0.5:
                l['gpr_hit'] = True
            if net_profit > (budget / 2):
            #if net_profit > 10000000:
                l['net_hit'] = True
        except TypeError:
            pass

    return leads

@contextmanager
def pool_context(*args, **kwargs):
    pool = mp.Pool(*args, **kwargs)
    yield pool
    pool.terminate()

def scrape_movies(movies, actor_name):
    # We need to rate limit ourselves doing this
    # This also give us time to parse through the html in a different thread?
    # Get the list of movie urls
    url_list = [(glob_url + m['URL'], m['Name']) for m in movies]
    final_list = []

    # Create a pool of workers and assign them each a url.
    print("Starting worker pool (10 workers)")
    with pool_context(processes=10) as pool:
        final_list = pool.map(partial(manip_movie, actor=actor_name), url_list)
    #print(final_list)
    print("Done working")

    # gonna try flattening that list, see what happens.
    final_list = filter(None, [i for sublist in filter(None, final_list) for i in sublist])
    #print(final_list)
    #for elm in final_list:
        #print(elm)

    #raise SyntaxError("DONE")
    out.write(final_list, actor_name)
    """
    for u in url_list:
        final_list.append(manip_movie(u, actor_name))
        manip_movie(u, actor_name)
        #sleep(5) # Sleep to be polite to IMDB
    """

