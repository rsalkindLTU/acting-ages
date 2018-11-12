import os as oos
from pathlib import Path

# This fill will eventually be used for writing all the good information to the disk
# it will take each actors name and list a things in a .csv for opening with an excel
# format to create the charts
save_path = "../out/"

def path_init():
    # Function to create the folder for the output files
    # Does nothing if the folder already exists
    if not Path(save_path).exists():
        try:
            oos.mkdir(save_path)
        except OSError:
            print("Creation of output file failed")
            raise
    else:
        pass

def writeFormatted(f_stream, args, collumn_offset = 0):
    for x in range(collumn_offset):
        f_stream.write(',')
    for a in args:
        if ',' in a:
            f_stream.write('"' + a  + '",')
        else:
            f_stream.write(a + ",")

    f_stream.write('\n')

def write_break(f_stream, count):
    # Automated way of adding newlines without wasting commas.
    for x in range(count):
        writeFormatted(f_stream, [])

def movie_group(actors, actor_name, f):
    # This function will take the list of actresses in one movie and
    # order them with the actor at the top, followed by their respective
    # ages in the movie.
    #print(actors)
    dude = None
    for a in actors:
        if a['actor'] == actor_name:
            dude = a
        else:
            pass

    writeFormatted(f, ['Movie:', 'Actor:', 'Actress:', 'Age:', 'Year:'], 2)
    writeFormatted(f, [dude['movie'], dude['actor'], '', str(dude['age']), str(dude['year'])], 2)


    for a in actors:
        if a['actor'] == actor_name:
            continue
        else:
            writeFormatted(f, [a['actor'], str(a['age'])], 4)

def write(actors, actor_name):
    path_init()
    # First order of buisness: Filter the list (again) into two seperate lists
    # One of the thrown out movies
    # The other of all good information

    thrown_data = []
    good_data = []
    for a in actors:
        if type(a) is str:
            thrown_data.append((a, 'doA'))
        elif a['gpr_hit'] is False and a['net_hit'] is False:
            thrown_data.append((a['movie'], 'not_hit'))
        else:
            filtered_data = {'actor':a['lead'], 'movie':a['movie'], 'age':a['age_at_release'], 'year':a['movie_year_released']}
            good_data.append(filtered_data)

    good_data = sorted(good_data, key=lambda k: k['year'])
    thrown_data = list(set(thrown_data))

    print("Good Data: ")
    print(good_data)
    print("Bad data: ")
    print(thrown_data)

    # Start writing!
    act_file_nm = actor_name +  "_results.csv"
    with open(oos.path.join(save_path, act_file_nm), "a") as f:

        # Loop over bad data first
        if len(thrown_data) is 0:
            writeFormatted(f, ['No Bad Data', actor_name])
        else:
            writeFormatted(f, ['Bad Data', actor_name])
            writeFormatted(f, ['Movie','Throw Reason'], 2)
            for t in thrown_data:
                writeFormatted(f, [t[0], t[1]], 2)

        # Now for the good data!
        if len(good_data) is 0:
            write_break(f, 3)
            writeFormatted(f, ['No Good Data', actor_name])
        else:
            write_break(f, 3)
            writeFormatted(f, ['Good Data', actor_name])
            writeFormatted(f, ['Movie'], 2)
            single_movie_data = []
            current_movie = good_data[0]['movie']
            for g in good_data:
                #writeFormatted(f, ['Nothing', 'Yet'], 2)
                if g['movie'] != current_movie:
                    #print("old m: " + current_movie + ", new m: " + g['movie'])
                    #print("current g actor: " + g['actor'])
                    current_movie = g['movie']
                    movie_group(single_movie_data, actor_name, f)
                    write_break(f, 1)
                    #writeFormatted(f, [])
                    single_movie_data = []
                    single_movie_data.append(g)
                else:
                    single_movie_data.append(g)
                    #print(g)

