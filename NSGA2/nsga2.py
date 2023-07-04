import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import nearest_points
from haversine import haversine
from tqdm import tqdm
import random
import math
import copy
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import warnings
warnings.filterwarnings('ignore')

customer = gpd.read_file('data/customer/customer.shp',encoding='utf-8')
depot = gpd.read_file('data/depot/depot.shp',encoding='utf-8')
depot['covered_idx'] = None

for i in range(len(depot)):
    cover = []

    for j in range(len(customer)):
        polygon = depot.geometry.iloc[i]
        point = customer.geometry.iloc[j]

        point, nearest_point = nearest_points(point, polygon)
        dist = haversine((point.y, point.x), (nearest_point.y, nearest_point.x), unit = 'm')
        
        # distance < 1km -> covered_idx
        if dist < 1000:
            cover.append(j)

    if len(cover) != 0:
        depot['covered_idx'][i] = cover

class Solution:
    def __init__(self, solution):
        self.solution = solution
        self.rank = None
        self.crowding_distance = None
        self.domination_count = 0
        self.dominated_individuals = set()
        self.objective_1, self.objective_2, self.objective_3 = get_objective_values(self.solution)

def get_objective_values(solution):
    # objective 1
    covered_list = []
    for idx in np.where(solution == 2)[0]:
        if depot.iloc[idx]['covered_idx'] is not None:
            covered_list += depot.iloc[idx]['covered_idx']
    covered_list = np.unique(covered_list)
    covered_num = sum([customer.iloc[idx]['demand'] for idx in covered_list])
    objective_1 = covered_num

    # objective 2
    cs = 0
    for idx in range(len(solution)):
        if solution[idx] == 0:
            pass
        elif solution[idx] == 1:
            cs += depot.iloc[idx]['area']*0.0656
        elif solution[idx] == 2:
            cs += depot.iloc[idx]['area']*0.1391
    objective_2 = cs

    # objective 3
    cost = 0
    for idx in range(len(solution)):
        if solution[idx] == 0:
            pass
        elif solution[idx] == 1:
            cost += depot.iloc[idx]['area']*180
        elif solution[idx] == 2:
            cost += depot.iloc[idx]['area']*1230
    objective_3 = cost/10000

    return objective_1, objective_2, objective_3

def fast_nondominated_sort(population):
    fronts = []
    first_front = []
    for p in population:
        p.rank = 0
        p.crowding_distance = 0
        p.domination_count = 0
        p.dominated_individuals = set()

    for p in population:
        for q in population:
            domination_score = 0
            if p.objective_1 > q.objective_1:
                domination_score += 1
            elif p.objective_1 == q.objective_1:
                domination_score += 0.5
            else:
                domination_score -= 10

            if p.objective_2 > q.objective_2:
                domination_score += 1
            elif p.objective_2 == q.objective_2:
                domination_score += 0.5
            else:
                domination_score -= 10
    
            if p.objective_3 < q.objective_3:
                domination_score += 1
            elif p.objective_3 == q.objective_3:
                domination_score += 0.5
            else:
                domination_score -= 10

            # p dominates q
            if domination_score > 1.5:
                q.domination_count += 1
                p.dominated_individuals.add(q)

    for p in population:
        if p.domination_count == 0:
            p.rank = 1
            first_front.append(p)

    fronts.append(first_front)
    i = 0
    while i < len(fronts):
        next_front = []
        for p in fronts[i]:
            for q in p.dominated_individuals:
                q.domination_count -= 1
                if q.domination_count == 0:
                    q.rank = i + 2
                    next_front.append(q)
        i += 1
        if next_front:
            fronts.append(next_front)
    return fronts

def crowding_distance_assignment(front):
    # eliminate duplicates
    unique_idx = []
    for idx in range(len(front)):
        if idx == 0:
            unique_idx.append(idx)
        else:
            past = front[idx-1].solution
            present = front[idx].solution
            if (past == present).all():
                pass
            else:
                unique_idx.append(idx)
    front = [front[idx] for idx in unique_idx]

    n = len(front)
    for m in range(3):
        if m == 0:
            front.sort(key=lambda p: p.objective_1)
            min_value = front[0].objective_1
            max_value = front[-1].objective_1
        elif m == 1:
            front.sort(key=lambda p: p.objective_2)
            min_value = front[0].objective_2
            max_value = front[-1].objective_2
        elif m == 2:
            front.sort(key=lambda p: p.objective_3)
            min_value = front[0].objective_3
            max_value = front[-1].objective_3
        
        front[0].crowding_distance = np.inf
        front[-1].crowding_distance = np.inf

        for i in range(1, n-1):
            p = front[i]
            if m == 0:
                distance = front[i+1].objective_1 - front[i-1].objective_1
            elif m == 1:
                distance = front[i+1].objective_2 - front[i-1].objective_2
            elif m == 2:
                distance = front[i+1].objective_3 - front[i-1].objective_3
            p.crowding_distance += distance / (max_value - min_value)

def tournament_selection(population, tournament_size):
    tournament = random.sample(population, tournament_size)
    tournament.sort(key=lambda p: (p.rank, -p.crowding_distance))
    return tournament[0]

def crossover(parent1, parent2, crossover_rate):
    if random.random() <= crossover_rate:
        sol1 = np.copy(parent1.solution)
        sol2 = np.copy(parent2.solution)
        idx = np.random.randint(len(sol1))
        sol = np.concatenate((sol1[:idx],sol2[idx:]))
        return sol
    else:
        return parent1.solution

def mutation(individual, mutation_rate):
    for idx in range(len(individual.solution)):
        if random.random() <= mutation_rate:
            individual.solution[idx] = np.random.randint(3)

def nsga2(population_size, num_generations, tournament_size, p_co, p_mut):
    population = [Solution(np.random.randint(3, size=len(depot))) for _ in range(population_size)]
    for _ in tqdm(range(num_generations)):
        is_full = False
        # elitism
        fronts = fast_nondominated_sort(population)
        parent = []
        for i in range(len(fronts)):
            crowding_distance_assignment(fronts[i])
            if len(parent) + len(fronts[i]) <= population_size/2:
                parent.extend(fronts[i])
            else:
                for element in fronts[i]:
                    if len(parent) == population_size/2:
                        is_full = True
                        break
                    else:
                        parent.append(element)
            if is_full:
                break
            i += 1

        # make offspring
        new_population = copy.deepcopy(parent)
        while len(new_population) < population_size:
            parent_1 = tournament_selection(parent, tournament_size)
            parent_2 = tournament_selection(parent, tournament_size)
            offspring_solution = crossover(parent_1, parent_2, p_co)
            offspring = Solution(offspring_solution)
            mutation(offspring, p_mut)
            offspring.objective_1, offspring.objective_2, offspring.objective_3 = get_objective_values(offspring.solution)
            new_population.append(offspring)

        population = new_population
    
    fronts = fast_nondominated_sort(population)

    pareto_fronts = []
    for front in fronts:
        elements = [[element.objective_1, element.objective_2, element.objective_3, element.solution] for element in front]
        pareto_fronts.append(elements)
    
    return pareto_fronts

def plot_3D(front):
    x = [row[0] for row in front]
    y = [row[1] for row in front]
    z = [row[2] for row in front]

    fig = plt.figure(figsize=(12,8))
    ax = fig.add_subplot(projection='3d')
    plot_3d = ax.scatter(x, y, z, c=z, cmap='cool', s=20, alpha=1)
    ax.set_xlabel('Objective 1', labelpad=-30)
    ax.set_ylabel('Objective 2', labelpad=-30)
    ax.set_zlabel('Objective 3', labelpad=-30)
    cbar = fig.colorbar(plot_3d)
    cbar.set_label('Cost', rotation=270, labelpad=10)
    plt.show()