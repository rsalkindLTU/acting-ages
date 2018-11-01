# This fill will eventually be used for writing all the good information to the disk
# it will take each actors name and list a things in a .csv for opening with an excel 
# format to create the charts

def write(actors, actor_name):
    # First order of buisness: Filter the list (again) into two seperate lists
    # One of the thrown out movies
    # The other of all good information

    thrown_data = []
    good_data = []
    for a in actors:
        if type(a) is str:
            thrown_data.append(a)
        elif type(a) is dict:
            filtered_data = {'actor':a['lead'], 'movie':a['movie'], 'age':a['age_at_release'], 'year':a['movie_year_released']}
            good_data.append(filtered_data)

    good_data = sorted(good_data, key=lambda k: k['year'])

    print("Good Data: ")
    print(good_data)
    print("Bad data: ")
    print(thrown_data)
    raise SyntaxError("The write module is not defined yet")

