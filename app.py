from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import json
import json
import os
import base64
from PIL import Image
from io import BytesIO


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:madmad@localhost/profile_database'
app.config['JSON_AS_ASCII']=False
SAVE_DIR = "./uploads/"


db = SQLAlchemy(app)


class Profile(db.Model):
    __tablename__ = 'profile'
    kakaoid = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    user = db.Column(db.String(10))  # member 또는 trainer
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    birthdate = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    belong = db.Column(db.String(50))
    history = db.Column(db.Text)
    image = db.Column(db.String(255))
    goal = db.Column(db.Text)  # goal을 int list로 저장
    tag = db.Column(db.Text)   # tag를 int list로 저장


class MatchRequest(db.Model):
    __tablename__ = 'match_requests'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_kakaoid = db.Column(db.String(255), nullable=False)
    receiver_kakaoid = db.Column(db.String(255), nullable=False)


class Matched(db.Model):
    __tablename__ = 'matched'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trainer_kakaoid = db.Column(db.String(255), nullable=False)
    member_kakaoid = db.Column(db.String(255), nullable=False)









def encode_image(image_path): #저장된 경로에 있는 이미지를 base64로 인코딩해서 반환
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read())
    return encoded.decode("utf-8")

def decode_image(encoded_string): # 인코딩된 스트링을 PIL의 Image로 반환
    if encoded_string == "": # 사용자의 이미지 정보가 없는 경우 None을 반환
        return None
    
    else : # 이미지가 있다면 decode해서 PIL Image로 반환
        image_data = base64.b64decode(encoded_string)
        image = Image.open(BytesIO(image_data))
        return image

def save_image(pil_image, path):
    pil_image.save(path)
    return path

def convert(str):
    if str == "":
        return []
    else:
        return list(map(int,str.split(",")))
    

# 카카오 로그인 아이디로 이미 등록된 프로필이 있는지 확인
# 없으면 null값 반환
# 있으면 profile을 json string으로 클라이언트에 보내주기
@app.route('/check/<kakaoid>', methods=['GET'])
def check_profile(kakaoid):
    existing_profile = Profile.query.filter_by(kakaoid=kakaoid).first()

    if existing_profile:
        if existing_profile.image == "":
            encoded_string = ""
        else : 
            encoded_string = encode_image(existing_profile.image)
        profile_data = {
            'kakaoid': existing_profile.kakaoid,
            'user': existing_profile.user,
            'name': existing_profile.name,
            'phone': existing_profile.phone,
            'birthdate': existing_profile.birthdate,
            'gender': existing_profile.gender,
            'belong': existing_profile.belong,
            'history': existing_profile.history,
            'image': encoded_string,
            'goal': convert(existing_profile.goal),
            'tag': convert(existing_profile.tag)
        }
        return json.dumps(profile_data, ensure_ascii=False), 200
    else:
        # 프로필이 없을 때
        return "", 204




# 프로필정보 받아서 db 저장
@app.route('/register', methods=['POST'])
def register_profile():
    data = json.loads(request.form.get('data'))

    new_profile = Profile(
        kakaoid=data['kakaoid'],
        user=data['user'],
        name=data['name'],
        phone=data['phone'],
        birthdate=data['birthdate'],
        gender=data['gender'],
        belong=data['belong'],
        history=data['history'],
        image=data['image'],  # 이미지 파일 경로 저장
        goal=','.join(map(str, data['goal'])),  # int list를 문자열로 변환
        tag=','.join(map(str, data['tag']))      # int list를 문자열로 변환
    )
    pil_image = decode_image(new_profile.image)
    if pil_image == None:
        new_profile.image = ""
    else :
        pil_image_path = SAVE_DIR + str(new_profile.kakaoid) + ".jpg"
        save_image(pil_image, pil_image_path)
        new_profile.image = pil_image_path
    db.session.add(new_profile)
    db.session.commit()

    return "Done"  # 응답 없음


    


# match 요청을 보내면, 각각 sender와 receiver에 저장한다.
@app.route('/send_match_request/<sender_kakaoid>/<receiver_kakaoid>', methods=['GET'])
def send_match_request(sender_kakaoid, receiver_kakaoid):
    try:
        match_request = MatchRequest.query.filter_by(sender_kakaoid=sender_kakaoid, receiver_kakaoid=receiver_kakaoid).first()
        if match_request:
            return "fail" 
        else: 
            match_requests=MatchRequest(
                sender_kakaoid=sender_kakaoid,
                receiver_kakaoid=receiver_kakaoid
            )   
            db.session.add(match_requests)
            db.session.commit()
            return ""
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


# match 요청을 받아들이면, matched에 trainer_kakaoid, member_kakaoid로 나눠서 저장한다. 
@app.route('/accept_match_request/<client_kakaoid>/<sender_kakaoid>/<accept>', methods=['GET'])
def accept_match_request(client_kakaoid, sender_kakaoid, accept):
    try:
        # 매치 요청 확인
        if accept=='1':
            # 클라이언트의 카카오 아이디와 일치하는 profile 정보 확인
            client_profile = Profile.query.filter_by(kakaoid=client_kakaoid).first()

            if client_profile:
                trainer_kakaoid = None
                member_kakaoid = None

                # 클라이언트의 user 유형 확인 (trainer 또는 member)
                if client_profile.user == 'Trainer':
                    trainer_kakaoid = client_kakaoid
                    member_kakaoid = sender_kakaoid
                elif client_profile.user == 'Member':
                    trainer_kakaoid = sender_kakaoid
                    member_kakaoid = client_kakaoid

                # matched 테이블에 매치 정보 저장
                matched = Matched(trainer_kakaoid=trainer_kakaoid, member_kakaoid=member_kakaoid)
                db.session.add(matched)
                db.session.commit()


        match_request=MatchRequest.query.filter_by(sender_kakaoid=sender_kakaoid, receiver_kakaoid=client_kakaoid).first()
        match_request_reverse=MatchRequest.query.filter_by(sender_kakaoid=client_kakaoid, receiver_kakaoid=sender_kakaoid).first()
        print(sender_kakaoid)
        print(client_kakaoid)
        # 매치 요청 삭제
        if match_request:
            db.session.delete(match_request)
        if match_request_reverse:
            db.session.delete(match_request_reverse)
        
        db.session.commit()

        return "Match request accepted and saved to matched table", 200


    except Exception as e:
        return jsonify({'error': str(e)}), 500





# profiles route에서,receiver안에 들었는지 여부를 확인하고,내가 receiver이면 짝인 sender의 프로필 정보를 requests list에 반환한다. 
    #(client가 trainer인지 member인지 우선 확인해야한다.)->profile table에서 trainer인지 먼저 확인한다. 
    #없으면 member. 그리고 matched table에서  나와 matched된 상대의 프로필 정보를 members list에 모두 반환한다.
@app.route('/profiles/<client_kakaoid>', methods=['GET'])
def get_profiles(client_kakaoid):
    try:
        # 모든 프로필 데이터 조회
        profiles = Profile.query.all()

        # 프로필 데이터를 JSON 형식으로 변환
        profile_list = []
        for profile in profiles:
            if profile.image == "":
                encoded_string = ""
            else : 
                encoded_string = encode_image(profile.image)
            profile_data = {
                'kakaoid': profile.kakaoid,
                'user': profile.user,
                'name': profile.name,
                'phone': profile.phone,
                'birthdate': profile.birthdate,
                'gender': profile.gender,
                'belong': profile.belong,
                'history': profile.history,
                'image': encoded_string,
                'goal': convert(profile.goal),
                'tag': convert(profile.tag)
            }
            profile_list.append(profile_data)


        # match_requests 테이블에서 현재 사용자가 수신자로 있는 매치 요청을 확인
        match_requests = MatchRequest.query.filter_by(receiver_kakaoid=client_kakaoid).all()
        #print(match_requests)
        #print(client_kakaoid)
        requests_list = []
        for match_request in match_requests:
            sender_kakaoid = match_request.sender_kakaoid
            #내가 receiver이면 짝인 sender의 프로필 정보를 requests list에 반환한다. 
            sender_profile = Profile.query.filter_by(kakaoid=sender_kakaoid).first()

            if sender_profile:
                if sender_profile.image == "":
                    encoded_string = ""
                else:
                    encoded_string = encode_image(sender_profile.image)
                request_data = {
                    'kakaoid': sender_profile.kakaoid,
                    'user': sender_profile.user,
                    'name': sender_profile.name,
                    'phone': sender_profile.phone,
                    'birthdate': sender_profile.birthdate,
                    'gender': sender_profile.gender,
                    'belong': sender_profile.belong,
                    'history': sender_profile.history,
                    'image': encoded_string,
                    'goal': convert(sender_profile.goal),
                    'tag': convert(sender_profile.tag)
                }
                requests_list.append(request_data)



        # 클라이언트의 유형 확인 (Trainer 또는 Member)
        client_profile = Profile.query.filter_by(kakaoid=client_kakaoid).first()
        client_user = client_profile.user if client_profile else None

        # matched 테이블에서 매칭된 프로필 정보 가져오기
        matches_list = []
        if client_user:
            if client_user == 'Trainer':
                trainer_kakaoid = client_kakaoid
                matches = Matched.query.filter_by(trainer_kakaoid=trainer_kakaoid).all()
            else:
                member_kakaoid = client_kakaoid
                matches = Matched.query.filter_by(member_kakaoid=member_kakaoid).all()

            for match in matches:
                partner_kakaoid = match.member_kakaoid if client_user == 'Trainer' else match.trainer_kakaoid
                partner_profile = Profile.query.filter_by(kakaoid=partner_kakaoid).first()

                if partner_profile:
                    if partner_profile.image == "":
                        encoded_string = ""
                    else:
                        encoded_string = encode_image(partner_profile.image)
                    match_data = {
                        'kakaoid': partner_profile.kakaoid,
                        'user': partner_profile.user,
                        'name': partner_profile.name,
                        'phone': partner_profile.phone,
                        'birthdate': partner_profile.birthdate,
                        'gender': partner_profile.gender,
                        'belong': partner_profile.belong,
                        'history': partner_profile.history,
                        'image': encoded_string,
                        'goal': convert(partner_profile.goal),
                        'tag': convert(partner_profile.tag)
                    }
                    matches_list.append(match_data)
        #print(profile_list, requests_list, matches_list, sep='\n')
        return json.dumps({'profiles': profile_list, 'requests': requests_list, 'matches': matches_list}, ensure_ascii=False), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='80')


