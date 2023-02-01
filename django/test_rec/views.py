from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import simplejson as json
import pandas as pd
import numpy
import pickle
import random
from pathlib import Path
from .models import TmpUser
import sys
sys.path.append('..')
from Utils import user_input_to_recommend, final_movie_select, user_input_to_side_recommend


def print_TmpUserInfo(user):
    print(f'userid: {user.id}')
    print(f'MBTI:{user.MBTI}')
    print(f'ennea_ans1:{user.ennea_ans1}')
    print(f'ennea_ans2:{user.ennea_ans2}')
    print(f'ennea_res:{user.ennea_res}')
    print(f'prefer_movie_id:{user.prefer_movie_id}')
    print(f'recommended_character_id:{user.recommended_character_id}')

pickle_path = Path(__file__).parent.parent.parent.absolute()/"Utils/Pickle"
movieId2poster_path = pickle_path / 'movieid_to_poster_file.pickle'


with open(movieId2poster_path,'rb') as f:
    movieId_to_posterfile = pickle.load(f)


character_df = pd.read_pickle(pickle_path / '230130_Popular_movie_character_2867_cwj.pickle')
movie_df = pd.read_pickle(pickle_path / '230130_Popular_movie_1192_cwj.pickle')
watch_link =  pd.read_pickle(pickle_path / '230131_watch_link_4679_rows.pickle')


@csrf_exempt
def start_test(request):
    return render(request, 'test_rec/main.html')


@csrf_exempt
def mbti_test(request):
    user = TmpUser.objects.create(create_time=timezone.now())
    request.session['user_id'] = user.id
    return render(request, 'test_rec/mbti.html')


@csrf_exempt
def enneagram_test(request):
    user = TmpUser.objects.get(id=request.session['user_id'])
    if request.method == 'POST':
        mbti = request.POST.get('MBTI')
        user.MBTI = mbti
        user.save()
    return render(request, 'test_rec/enneagram.html')


@csrf_exempt
def enneagram_test2(request):
    user = TmpUser.objects.get(id=request.session['user_id'])
    if request.method == 'POST':
        ans1 = request.POST.get('enneagram1')
        user.ennea_ans1 = ans1
        user.save()
    return render(request, 'test_rec/enneagram2.html')


@csrf_exempt
def enneagram_test3(request):
    user = TmpUser.objects.get(id=request.session['user_id'])
    # 이전페이지의 애니어그램 답변2 받아서 유저정보에 저장
    if request.method == 'POST':
        ans2 = request.POST.get('enneagram2')
        user.ennea_ans2 = ans2
        user.save()
    # 유저정보에 저장된 애니어그램 답변을 바탕으로 추가질문 불러오기
    engram_crite = user.ennea_ans1 + user.ennea_ans2
    df = pd.read_pickle(pickle_path / 'enneagram_question.pickle')
    add_quest = df[df.base==engram_crite][['question','three_letter']].copy()
    add_quest_list = add_quest.to_dict(orient='records')
    return render(request, 'test_rec/enneagram3.html', {'add_quest_list': add_quest_list})


@csrf_exempt
def movie_test(request):
    
    user = TmpUser.objects.get(id=request.session['user_id'])

    # 이전 페이지의 애니어그램 답변3 받아서 유저정보에 저장 (1w2 형식)
    if request.method == 'POST':
        ans3 = request.POST.get('enneagram3')
        user.ennea_res = ans3
        user.save()

    # 추천할 영화리스트 불러오기
    N_movies=100
    seed = random.randint(0,int(1e6))
    print(f">>>{seed = }")
    selec_movie_ids = list(set(final_movie_select(seed, N_movies)))

    print(f">>>>>>>>>>>>>{len(selec_movie_ids)}")
    poster_file_list = [movieId_to_posterfile[id] for id in selec_movie_ids]
    print(f"{len(selec_movie_ids)=},  {len(poster_file_list)=}, {len(set(poster_file_list))=}")
    paginator1 = Paginator(poster_file_list, 20)
    page_number = request.GET.get('page') or 1
    page_obj1 = paginator1.get_page(page_number)

    movieid2kotitle = dict(zip(movie_df.movieId, movie_df.ko_title))
    ko_title_list = [movieid2kotitle[id] for id in selec_movie_ids]
    paginator2 = Paginator(ko_title_list, 20)
    page_number = request.GET.get('page') or 1
    page_obj2 = paginator2.get_page(page_number)

    ziped_page_obj = zip(page_obj1, page_obj2)

    context = {
        'length' : len(poster_file_list),
        'page_obj': page_obj1,
        'zip_page_obj': ziped_page_obj
    }
    return render(request, 'test_rec/movie.html', context)


@csrf_exempt
def result_page(request):

    user = TmpUser.objects.get(id=request.session['user_id'])
    
    if request.method == 'POST':
        # 이전 페이지의 영화선택 받아서 유저정보에 저장
        movies = request.POST.getlist('movies')
        movie_list = [i.split('_')[0] for i in movies]
        print(f"{movie_list=}")
        if movie_list:
            user.prefer_movie_id = json.dumps(movie_list)
            # 유저정보가 선호한 영화리스트를 바탕으로 캐릭터 추천
            movie_list = [int(i) for i in movie_list]
            
            interaction_movie_list = [i for i in movie_list if i < 300_000]
            side_info_movie_list = [i for i in movie_list if i >= 300_000]

            fit_mbti_dict_path = pickle_path / '230201_fit_mbti_dict.pickle'
            with open(fit_mbti_dict_path, 'rb') as f:
                 fit_mbti_dict = pickle.load(f)
            user_fit_MBTI = fit_mbti_dict[user.MBTI]
            mbti_list=[user.MBTI,user_fit_MBTI]
            result=pd.DataFrame()
            if interaction_movie_list:
                result1 = user_input_to_recommend(mbti_list, user.ennea_res, interaction_movie_list, 100)
                result = pd.concat([result, result1])
                print('>>>>',result1.shape)
            if side_info_movie_list:
                result2 = user_input_to_side_recommend(mbti_list, user.ennea_res, interaction_movie_list, 100)
                result = pd.concat([result, result2])
                print('>>>>',result2.shape)
            print(f"{result.shape=}")
            result = result[result.Enneagram_sim.notna()]
            result.Enneagram_sim = result.Enneagram_sim.map(lambda x: int(round(x*100)))
            characterid_to_hashtag_path = pickle_path / '230201_characterid_to_hashtag.pickle'
            with open(characterid_to_hashtag_path, 'rb') as f:
                characterid_to_hashtag = pickle.load(f)
            # 추천된 캐릭터 유저정보에 저장
            character_list = result['CharacterId'].values.tolist()
            character_list = [str(i) for i in character_list]
            user.recommended_character_id = json.dumps(character_list)
            user.save()
            # 추천된 캐릭터 리스트를 바탕으로 html에 뿌려주기
            cols=['CharacterId','Character','ko_title','MBTI','img_src','hashtag','npop','Enneagram_sim']
            result = result.merge(movie_df[['movieId','ko_title','npop']])
            result['hashtag'] = result.CharacterId.map(characterid_to_hashtag)
            print(result[cols][:3])
            character_df
            result_list = result[result.MBTI==user.MBTI][cols][:20].to_dict(orient='records')
            paginator = Paginator(result_list, 20)
            page_number = request.GET.get('page') or 1
            page_obj = paginator.get_page(page_number)
            
            result_list2 = result[result.MBTI==user_fit_MBTI][cols][:20].to_dict(orient='records')

            context = {"data1": result_list, 'data2':result_list2, 'page_obj': page_obj}
            return render(request, 'test_rec/result.html', context)
        else:
            return render(request, 'test_rec/result.html')


@csrf_exempt
def result_movie(request, character_id):
    need_cols=['Character','movieId']
    character_name, movie_id = character_df[character_df.CharacterId==int(character_id)][need_cols].values[0]
    posterfile_path = movieId_to_posterfile[movie_id]
    movie_title, genres, plot = movie_df[movie_df.movieId==movie_id][['ko_title','ko_genre','ko_plot']].values[0]
    result_movie ={
        'name': character_name,
        'movie' : movie_title,
        'img_path' : posterfile_path,
        'genres' : genres,
        'plot' : plot
    }
    # print(result_movie)
    links_df = watch_link[watch_link.movieId==movie_id][['platform','link']]
    links = links_df.to_dict(orient='records')
    # print(links)
    context = {'data': result_movie, 'links': links}
    return render(request, 'test_rec/result_movie.html', context)
