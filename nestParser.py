#!python3
#-*- coding: utf-8 -*-
import os
import sys
import json
import webbrowser
import operator
from math import ceil
from geopy.distance import vincenty


def dump_poke_groups(poke_groups, pokeGroups):
    data = []
    for groupNum in range(pokeGroups):
        groupId = '@'+str(groupNum)
        groupNode = poke_groups[groupId]
        data.append(groupNode[1])
    with open('data/locs.json', 'w') as locs:
        json.dump(data, locs, indent=2)

def add_nest(poke_groups, pokeGroups):
    print('\n- New Nest -')
    name = input('Name: ')
    coords = None
    while (coords == None):
        coords = input('Lat,Lng: ')
        if ('http' in coords):
            coords = coords.split('@')[1]
        coords = coords.split(',')
        try:
            lat, lng = float(coords[0]), float(coords[1])
        except:
            coords = None
    rad = None
    while (rad == None):
        try:
            rad = int(input('Radius: '))
        except:
            pass
    aux = input('Common list: ')
    if (aux != ''):
        common = aux.split(',')
        for i in range(len(common)):
            common[i] = common[i].strip()
    else:
        common = []
    node = [[],{}]
    groupId = '@'+str(pokeGroups)
    poke_groups[groupId] = node
    pokeGroups += 1
    update_nest(poke_groups, pokeGroups, groupId, lat, lng, name, rad, common)
    return poke_groups, pokeGroups

def update_nest(poke_groups, pokeGroups, groupId, lat=None, lng=None, name=None, rad=None, common=None):
    groupNode = poke_groups[groupId]
    groupInfo = groupNode[1]
    if (lat != None):
        groupInfo['lat'] = lat
    if (lng != None):
        groupInfo['lng'] = lng
    if (name != None):
        groupInfo['name'] = name
    if (rad != None):
        groupInfo['rad'] = rad
    if (common != None):
        groupInfo['common'] = common
    dump_poke_groups(poke_groups, pokeGroups)
    return poke_groups
    
def add_spawn(spawnInfo, poke_groups, pokeGroups):
    joined = spawnInfo['joined']
    closerId = None
    closerDist = None
    while (spawnInfo['joined'] == 0):
        for groupNum in range(pokeGroups):
            groupId = '@'+str(groupNum)
            groupNode = poke_groups[groupId]
            groupInfo = groupNode[1]
            point1 = (spawnInfo['lat'],spawnInfo['lng'])
            point2 = (groupInfo['lat'],groupInfo['lng'])
            dist = vincenty(point1, point2)
            if (dist.meters <= groupInfo['rad']):
                spawnInfo['joined'] += 1
                groupNode[0].append((spawnInfo,dist.meters))
            else:
                if (closerId == None) or (dist.meters < closerDist):
                    closerId = groupId
                    closerDist = dist.meters
            
        if spawnInfo['joined'] == 0:
            closerInfo = poke_groups[closerId][1]
            pos = str(spawnInfo['lat']) + ',' + str(spawnInfo['lng'])
            print ('\nSpawn at [' + pos + '] outside of any nest range.')
            url = 'https://www.google.com/maps/?q=' + pos
            webbrowser.open(url)
            print('Closer nest identified: ' + closerInfo['name'] + ' (Radius: ' + str(closerInfo['rad']) + 'm)')
            print('Increase range of \'' + closerInfo['name'] + '\' to ' + str(ceil(closerDist)) + 'm?')
            choice = ''
            while (choice == ''):
                choice = input('y or n: ')
                choice = choice.lower()
                if (choice == 'y'):
                    poke_groups = update_nest(poke_groups, pokeGroups, closerId, rad=ceil(closerDist))
                elif (choice == 'n'):
                    poke_groups, pokeGroups = add_nest(poke_groups, pokeGroups)
                else:
                    choice = ''
    return poke_groups, pokeGroups

def parse_groups(nest_locs, poke_spawns):
    poke_groups = {}
    pokeGroups = 0
    
    for loc in nest_locs:
        node = [[],loc]
        poke_groups['@'+str(pokeGroups)] = node
        pokeGroups += 1
    for spawnInfo in poke_spawns:
        spawnInfo.pop('time', None)
        spawnInfo['joined'] = 0
        poke_groups, pokeGroups = add_spawn(spawnInfo, poke_groups, pokeGroups)
    
    return poke_groups, pokeGroups

def eval_nests(poke_groups, pokeGroups):
    for groupNum in range(pokeGroups):
        poke_count = {}
        dup_check = {}
        groupId = '@'+str(groupNum)
        groupNode = poke_groups[groupId]
        if (groupNode[1]['rad'] == 0):
            continue
        all_dup = True
        for spawnNode in groupNode[0]:
            spawnInfo = spawnNode[0]
            pokeId = spawnInfo['pokemonId']
            if pokeId in poke_count:
                poke_count[pokeId] += 1
            else:
                poke_count[pokeId] = 1
            if (spawnInfo['joined'] > 1):
                if pokeId in dup_check:
                    dup_check[pokeId] += 1
                else:
                    dup_check[pokeId] = 1
            else:
                all_dup = False
        for dup_key in dup_check:
            if (not all_dup and poke_count[dup_key] <= dup_check[dup_key]):
                poke_count[dup_key] *= -1
        yield groupNode, sorted(poke_count.items(), key=operator.itemgetter(1), reverse=True)
        
def print_nest(groupNode, nestInfo, poke_list, global_common):
    nest_common = set(global_common + groupNode[1]['common'])
    os.system('cls' if os.name == 'nt' else 'clear')
    pos_len = len(nestInfo)
    neg_len = 0
    i = pos_len - 1
    while (i >= 0 and nestInfo[i][1] < 0):
        pos_len -= 1
        neg_len += 1
        i -= 1
    print ('- ' + groupNode[1]['name'] + ' -')
    total_len = len(groupNode[0]) - neg_len
    i = 0
    while (i < pos_len and (nestInfo[i][1] / total_len) > 0.1):
        id = nestInfo[i][0] - 1
        name = poke_list[id]
        if name not in nest_common:
            print('Possible nest of:', name)
            i = pos_len
        else:
            i += 1
    print('\nUncommon spawning rate:')
    for i in range(0, pos_len):
        id = nestInfo[i][0] - 1
        name = poke_list[id]
        if name not in global_common:
            spawnCount = nestInfo[i][1]
            print('%-12s' % (name), '\t-\t' + '%2.f' % ((spawnCount / total_len)*100) + '% (' + str(spawnCount) + ' out of ' + str(total_len) + ')')
    print('\nCommon spawning rate:')
    for i in range(0, pos_len):
        id = nestInfo[i][0] - 1
        name = poke_list[id]
        if name in global_common:
            spawnCount = nestInfo[i][1]
            print('%-12s' % (name), '\t-\t' + '%2.f' % ((spawnCount / total_len)*100) + '% (' + str(spawnCount) + ' out of ' + str(total_len) + ')')
    if (neg_len > 0):
        print('\nLikely misplaced spawns rate:')
        for i in range(-1, (-1*neg_len)-1, -1):
            id = nestInfo[i][0] - 1
            name = poke_list[id]
            spawnCount = nestInfo[i][1] * -1
            total_len = len(groupNode[0])
            print('%-12s' % (name), '\t-\t' + '%2.f' % ((spawnCount / total_len)*100) + '% (' + str(spawnCount) + ' out of ' + str(total_len) + ')')
    input('\nPress any key to continue . . . ')
    
def load_data():
    i = 0
    while (i < 4):
        try:
            file = 'data/locs.json'
            with open(file, 'r') as locs:
                nest_locs = json.load(locs)
            i += 1
            file = 'data/pokealert_spawn_points.json'
            with open(file, 'r') as spawns:
                poke_spawns = json.load(spawns)
            i += 1
            file = 'data/common_pokemon.json'
            with open(file, 'r') as commons:
                global_common = json.load(commons)
            i += 1
            file = 'data/pokemon_list.json'
            with open(file, 'r') as pokemons:
                poke_list = json.load(pokemons)
            i += 1
        except FileNotFoundError:
            print('\nFile', '\"' + file + '\"', 'not found.')
            exampleFile = file.rstrip('json')[:-1] + '-example' + '.json'
            try:
                with open(exampleFile, 'r') as example:
                    data = json.load(example)
                print('Creating it with the contents of', '\"' + exampleFile + '\"' + '.')
                with open(file, 'w+') as out:
                    json.dump(data, out, indent=2)
            except:
                raise
            i = 0
        except:
            if (i == 0):
                print('Incorrect data on \'locs.json\' file.',)
            elif (i == 1):
                print('Incorrect data on \'pokealert_spawn_points.json\' file.',)
            elif (i == 2):
                print('Incorrect data on \'common_pokemon.json\' file.',)
            else:
                print('Incorrect data on \'pokemon_list.json\' file.')
            raise
    return nest_locs, poke_spawns, poke_list, global_common
    
if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')
    try:
        nest_locs, poke_spawns, poke_list, global_common = load_data()
    except:
        print('bug')
        sys.exit()
    if (len(nest_locs) == 0):
        print('No nest location found on \'locs.json\'')
        sys.exit()
    if (len(poke_spawns) == 0):
        print('No spawn point found on \'pokealert_spawn_points.json\'')
        sys.exit()
    
    poke_groups, pokeGroups = parse_groups(nest_locs, poke_spawns)
    input('\nNests parsed! Press any key to start . . . ')
    for groupNode, nestInfo in eval_nests(poke_groups, pokeGroups):
        print_nest(groupNode, nestInfo, poke_list, global_common)
    os.system('cls' if os.name == 'nt' else 'clear')
    input('Press any key to continue . . . ')
