from datetime import datetime
import scrape as sc
import re

glob_url = 'https://imdb.com/'

def related_movies(raw_html):
    print('Finding related movies...')
    # Take the normal html and load it into BS4
    html = sc.BeautifulSoup(raw_html, 'html.parser')

    # Find all the div's with an id with the pattern 'actor-tt******' where the *'s are random numbers that we dont care about
    movie_soup = html.findAll('div', {'id': re.compile('actor-tt.')})
    #movie_soup = html.find('div', {'class': 'filmo-category-section'}).findAll('div', recursive=False)

    # Pre defined dictionarys
    movie_list = []
    # For each element of both, get the movie name, url, and the year it was made.
    for elm in movie_soup:
        #Clause to filter out T.V shows
        if elm.find('div', {'class':'filmo-episodes'}) is not None:
            continue
        mov_name = str(elm.b.a.text)

        mov_url = elm.b.a['href']
        # Cut off any extrenious year information to make filtering easier later.
        mov_url = mov_url[:17]

        mov_year = elm.span.text.strip() # we have to strip the whitespace afterwards

        #print('{0} - {1} - {2}'.format(mov_name, mov_url, mov_year))
        movie_list.append({'Name':mov_name, 'URL':mov_url, 'Year':mov_year})

    print ('Done finding related movies')
    # Return the list, sorted by year (ascending)
    return sorted(movie_list, key=lambda k: k['Year'])

def get_actor_name(raw_html):
    html = sc.BeautifulSoup(raw_html, 'html.parser')
    # Get the actor's name from the title
    soup = html.find('span', {'class': 'itemprop'})
    return soup.text

def trim_here(m):
    current_year = datetime.now().year
    if m['Year'] is '' or int(m['Year'][:4]) > current_year:
        return False
    return True

def trim_movie_list(movies):
    print("Trimming movie list...")
    trimmed_movies = [m for m in movies if trim_here(m)]

    print("Done trimming movie list...")
    return trimmed_movies

if __name__ == '__main__':

    act = [#'/name/nm0000553/', # Liam Nissan
           #'/name/nm0000129/', # Tom Cruise
           #'/name/nm0000123/', # George Clooney
           #'/name/nm0000125/', # Sean Connery
           #'/name/nm0000354/', # Matt Damon
           #'/name/nm0000148/', # Harrison Ford
           '/name/nm0000243/'] # Denzel Washington

    for a in act:
        raw_html = sc.simple_get(glob_url + a)
        actor_name = get_actor_name(raw_html)
        final = trim_movie_list(related_movies(raw_html))

        print(str(len(final)) + ' items')

        print("Working on actor: " + actor_name)
        sc.scrape_movies(final, actor_name)

    #for e in final:
        #print('{0:60} | {1:20} | {2}'.format(e['Name'], e['URL'], e['Year']))
    #print(str(len(final)) + ' items')

    # Time to scrape!
    #sc.scrape_movies(final, actor_name)
