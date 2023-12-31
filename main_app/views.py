from django.shortcuts import render
from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .eval_module import Evaluate
from .DATA import TestModulesHistory,TestTotalMarks
from .Database_functions import MongoInsertTest,MongoInsertTotalMark,MongoRetirveTest,MongoRetirveTotalMarks,InsertRating,RetriveRating,RetriveResources,SeniorProfiles,MongoGetAllUsers
import logging
from django.conf import settings
from django.core.mail import send_mail
from .emails import send_result_mail
import threading
import multiprocessing


# Create your views here.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs.log"),
    ],)



def new_user_background_task(email,password,logger): #background task to create new user
    user = User.objects.create_user(username=email,password=password)
    user.save()
    logger.info("User {} Created Successfully".format(email))

    new_user_test_modeule = {
        "user_id":email,
        "scores":TestModulesHistory,
    }

    new_user_total_marks = {
        "user_id":email,
        "scores":TestTotalMarks,
    }

    MongoInsertTest(new_user_test_modeule)
    MongoInsertTotalMark(new_user_total_marks)
    print("new_user_test_modeule:",new_user_test_modeule)
    print("new_user_total_marks:",new_user_total_marks)

class RegisterNewUser(APIView):
    def post(self,request):
        logger = logging.getLogger("RegisterNewUser")
        email = request.data.get("email")
        password = request.data.get("password")

        if password is None or email is None:
            return Response({"message":"Please provide all the details"})
        
        try:
            new_user_background_task_t = threading.Thread(target=new_user_background_task,args=(email,password,logger))
            new_user_background_task_t.start()

            return Response({"message":"User {} Created Successfully".format(email)})
        except Exception as e:
            logging.error("User {} Already Exists".format(email))
            print(e)
            return Response({"message":"User {} Already Exists".format(email)})
        

class Greeting(APIView):
    permission_classes = ( IsAuthenticated, )
    def get(self,request):
        logger = logging.getLogger("Greeting")
        user = request.user.username

        logger.info("User {} came in".format(user))

        subject = "testing the mail functions"
        message = "Hi {} welcome to skillpulse".format(user)
        email_from = settings.EMAIL_HOST_USER
        recipient_list = ["arjunprakash027@gmail.com",]

        try:
            send_mail( subject, message, email_from, recipient_list)
            print("mail sent")
        except Exception as e:
            print(e)
            print("mail not sent")

        return Response({"message":"HI {}".format(user)})
    

class TestHistory(APIView):
    permission_classes = ( IsAuthenticated, )
    def get(self,request):
        
        user = request.user.username
        logger = logging.getLogger("TestHistory")
        logger.info("User {} came in".format(request.user.username))
        output = MongoRetirveTest(user)
        return Response(output["scores"])
    

class TestMark(APIView):
    permission_classes = ( IsAuthenticated, )
    def get(self,request):
        
        user = request.user.username
        logger = logging.getLogger("TestMark")
        logger.info("User {} came in".format(request.user.username))
        output = MongoRetirveTotalMarks(user)
        return Response(output["scores"])
    
class RatingRetrive(APIView):
    permission_classes = ( IsAuthenticated, )
    def get(self,request):
        
        user = request.user.username
        logger = logging.getLogger("RatingRetrive")
        logger.info("User {} came in".format(request.user.username))
        if user == "test@gmail.com":
            subject = request.query_params.get("subject")
        else:
            subject = request.data.get("subject")
        output = RetriveRating(user,subject)
        print(output)
        return Response(output["ratings"])

class ResourcesRetreive(APIView):
    permission_classes = ( IsAuthenticated, )
    def post(self,request):

        user = request.user.username
        logger = logging.getLogger("ResourcesRetreive")
        logger.info("User {} came in".format(request.user.username))
        if user == "test@gmail.com":
            subject = request.query_params.get("subject")
        else:
            subject = request.data.get("subject")
        
        print(subject)
        
        output = RetriveResources(user,subject)
        print(output)
        return Response({"resources":output})

class GetUserAnswersmcq(APIView):
    permission_classes = ( IsAuthenticated, )
    def post(self,request):
        logger = logging.getLogger("GetUserAnswersmcq")
        logger.info("User {} came in".format(request.user.username))
        user_res = request.data.get("UserAnswer")

        for x in user_res:
            subject = x

        avilable_answers = []
        for i in user_res[subject]:
            if user_res[subject][i] == "":
                continue
            else:
                avilable_answers.append(i)

        print(subject)
        print('I see this',user_res)
        print(avilable_answers)
        
        SubmitUserAns = Evaluate(subject,avilable_answers,request.user.username)
        SubmitUserAns.mcqPercentage(user_res[subject])

        return Response("working well")


def background_task(subject,avilable_answers,username,user_res): #this is the background task that sends user answer to chatgpt to retreive ratings
    ai = Evaluate(subject,avilable_answers,username)

    prompt=ai.generate_prompt(user_res)
    print(prompt)
    scores=ai.extraction(x:=ai.generate_chat_response(prompt))

    print("gpt generated response:",x)
    print("scores of the user:",scores)
    
    rating = ai.jsonify(scores)
    
    Indirating = {
        "user_id":username,
        "subject":subject,
        "ratings":rating
    }
    InsertRating(Indirating)

    #send_result_mail(rating,subject,username)

class GetUserAnswers(APIView):
    permission_classes = ( IsAuthenticated, )
    def post(self,request):
        logger = logging.getLogger("GetUserAnswers")
        logger.info("User {} came in".format(request.user.username))
        if request.user.username == "test@gmail.com":
            print("test enter")
            user_res = request.data.get("UserAnswer")
        else:
            user_res = request.data.get("UserAnswer")
        print(user_res)
        for x in user_res:
            subject = x
        print(subject)
        avilable_answers = []
        for i in user_res[subject]:
            if user_res[subject][i] == "":
                continue
            else:
                avilable_answers.append(i)
        print(avilable_answers)

        # ai = Evaluate(subject,avilable_answers,request.user.username)
        # prompt=ai.generate_prompt(user_res)
        # print(prompt)
        # scores=ai.extraction(x:=ai.generate_chat_response(prompt))

        # print("gpt generated response:",x)
        # print("scores of the user:",scores)
        
        # rating = ai.jsonify(scores)
        
        # Indirating = {
        #     "user_id":request.user.username,
        #     "subject":subject,
        #     "ratings":rating
        # }
        # InsertRating(Indirating)

        # send_result_mail(rating,subject,request.user.username)
        
        # background_task_t = threading.Thread(target=background_task,args=(subject,avilable_answers,request.user.username,user_res,))
        # background_task_t.start()

        background_task(subject, avilable_answers, request.user.username, user_res)

        return Response({"scores":"processing in background"})

class SeniorData(APIView):
    permission_classes = ( IsAuthenticated, )
    def get(self,request):
        logger = logging.getLogger("SeniorData")
        logger.info("User {} came in".format(request.user.username))
        result = SeniorProfiles()
        return Response({'senior_profiles':result})
    
class GetScoreboard(APIView):
    logger = logging.getLogger("GetScoreboard")
    logger.info("getting accessed")
    def get(self,request):
        score_board = {}
        all_scores = {}
        for x in MongoGetAllUsers():
            print(x['user_id'])
            score_board[x['user_id']] = 0
            all_scores[x['user_id']] = {"m1":{"entryTest":x['scores']['entryTest']['m1'],"exitTest":x['scores']['exitTest']['m1']}
                                        ,"m2":{"entryTest":x['scores']['entryTest']['m2'],"exitTest":x['scores']['exitTest']['m2']}}

            for scores,values in x['scores']['entryTest']['m1'].items():
                if values['totalMarks'] > 0:
                    score_board[x['user_id']] += (values['totalMarks']/4)*10
                else:
                    score_board[x['user_id']] += 0

            for scores,values in x['scores']['entryTest']['m2'].items():
                if values['totalMarks'] > 0:
                    score_board[x['user_id']] += (values['totalMarks']/3)*10
                else:
                    score_board[x['user_id']] += 0
        print({"all_scores":all_scores,"score_board":score_board})
        return Response({"all_scores":all_scores,"score_board":score_board})

