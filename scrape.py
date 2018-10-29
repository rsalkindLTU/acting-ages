# For url grabbing
from requests import get
from requests.exceptions import RequestException
from contextlib import closing

# For url parsing and scraping
from bs4 import BeautifulSoup

# Workers and multiprocessing
import multiprocessing as mp
from functools import partial
from contextlib import contextmanager

# sleep (not needed anymore?)
from time import sleep

glob_url = 'https://imdb.com/'

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
    html = simple_get(url)
    soup = BeautifulSoup(html, 'html.parser')

    # 1:
    lead_list = []
    lead_age = 0
    movie_page = soup.findAll('div', {'class' : 'credit_summary_item'})[2]
    leads = movie_page.findAll('a')

    # TODO: Refactor this part to be more dynamic
    if (leads[0].text != actor and
       leads[1].text != actor and
       leads[2].text != actor):
        return None

    lead_list.append({'lead':leads[0].text or False, 'lead_url':leads[0]['href'][1:16], 'gender':''})
    lead_list.append({'lead':leads[1].text or False, 'lead_url':leads[1]['href'][1:16], 'gender':''})
    lead_list.append({'lead':leads[2].text or False, 'lead_url':leads[2]['href'][1:16], 'gender':''})
    #print(lead_list)

    # 2: The actor needs a female counterpart
    for l in lead_list:
        # Check if any of the leads are female. Otherwise, return None
        act_html = simple_get(glob_url + l['lead_url'])
        act_soup = BeautifulSoup(act_html, 'html.parser')
        act_gender = act_soup.find('a', {'href':'#actor'})

        # Skip dudes
        if act_gender is not None:
            l['gender'] = 'm'
        else:
            l['gender'] = 'f'

    count = 0
    for l in lead_list: # If there are the male leads, there are no female leads.
        if l['gender'] == 'm':
            count += 1

    if count is 3:
        return None

    # Trim the list (again) to remove any other male stars:
    for x in range(len(lead_list)):
        if lead_list[x]['gender'] == 'm' and lead_list[x]['lead'] != actor:
            #del lead_list[x]
            lead_list[x] = None # Have to do it this way because python lists are dumb


    # 3: The movie needs to be considered a 'hit'
    # This one is more complex. We can do it based off of net gross or IMDB/Metacritic ratings, both work.
    #return True
    return lead_list

@contextmanager
def pool_context(*args, **kwargs):
    pool = mp.Pool(*args, **kwargs)
    yield pool
    pool.terminate()

def scrape_movies(movies, actor_name):
    # We need to rate limit ourselves doing this
    # This also give us time to parse through the html in a different thread?
    # Get the list of movie urls
    url_list = [glob_url + m['URL'] for m in movies]
    final_list = []

    # Create a pool of workers and assign them each a url.
    print("Starting worker pool (10 workers)")
    with pool_context(processes=10) as pool:
        final_list = pool.map(partial(manip_movie, actor=actor_name), url_list)
    print(final_list)
    print("Done working")

    """
    for u in url_list:
        final_list.append(manip_movie(u, actor_name))
        manip_movie(u, actor_name)
        #sleep(5) # Sleep to be polite to IMDB
    """

