# -*- coding: utf-8 -*-

# This is a High Low Guess game Alexa Skill.
# The skill serves as a simple sample on how to use the
# persistence attributes and persistence adapter features in the SDK.
import random
import logging
import os
import boto3

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response
from ask_sdk_s3.adapter import S3Adapter

SKILL_NAME = 'Cookie'
USER_NAME = 'user'
bucket_name = os.environ.get('S3_PERSISTENCE_BUCKET')
s3_client = boto3.client('s3',
                         region_name=os.environ.get('S3_PERSISTENCE_REGION'),
                         config=boto3.session.Config(signature_version='s3v4',s3={'addressing_style': 'path'}))
s3_adapter = S3Adapter(bucket_name=bucket_name, path_prefix="Media", s3_client=s3_client)
sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    """Handler for Skill Launch.

    Get the persistence attributes, to figure out the game state.
    """
    # type: (HandlerInput) -> Response
    attr = handler_input.attributes_manager.persistent_attributes
    if not attr:
        attr['morning_convo_state'] = -1
        attr['morning_convo_explored'] = []

    handler_input.attributes_manager.session_attributes = attr

    speech_text = ("Welcome to the Cookie. How are you doing today? ")
    reprompt = "Tell Cookie how you are doing today."

    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response


# ----------------------------------------------------------------------------------------------------------- #
# -----------------------------------MORNING CONVO START----------------------------------------------------- #
# ----------------------------------------------------------------------------------------------------------- #
# Morning convo states:
# -10 = convo has been terminanted. 
# -1  = convo has yet to begin, user can say yes to proceed with first question
# 1   = sleep quality prompt
    # 11 = good sleep quality, dream prompt
    # 16 = poor sleep quality reason prompt  { restlessness, getting up to go to the bathroom, nightmare, nightsweats/bad temperature, other } 
# 2   = pain assessment prompt
    # 21 = 
# 3   = morning medication check
# 4   = breakfast prompt

def morning_convo_state_match(handler_input, i):
    """Function that acts as can handle for game state."""
    # type: (HandlerInput) -> bool
    is_currently_playing = False
    sess_attr = handler_input.attributes_manager.session_attributes

    if ("morning_convo_state" in sess_attr and sess_attr['morning_convo_state'] == i):
        is_currently_playing = True
    return is_currently_playing

# Get the next random morning prompt
# attr['morning_convo_state'] 0 or rand[1,4] --> new rand[1,4]
def get_next_morning_prompt( attr ):
    # if we've explored all of the branches
    if len(attr['morning_convo_explored'] == 4) :
        st = "Thank you for taking the time to answer my questions."
        " Let Cookie know when you want to talk again, have a good rest of your morning!!"
        rp = None
        attr['morning_convo_state'] = -10
        return st, rp
    
    #convo_route = -1
    while convo_route == -1 or convo_route in attr['morning_convo_explored']:
        convo_route = random.randint(1,4)
    attr['morning_convo_state'] = convo_route
    st = ""
    rp = ""
    
    if convo_route == 1:
        st += "How did you sleep last night?"
        rp += "Give Cookie a quality rating to your sleep last night."
    elif convo_route == 2:
        st += "Are you experiencing any pain this morning?"
        rp += "Say yes or no to tell Cookie if you are in pain"
    elif convo_route == 3:
        st += "Have you taken your pills this morning?"
        rp += "Say yes or no to tell Cookie if you have taken your pills."
    else: # convo_route == 4:
        st += "Have you eaten breakfast yet?"
        rp += "Say yes or no to tell Cookie if you have eaten breakfast yet."
    
    return st, rp

# User can say they have time to answer some questions
@sb.request_handler(can_handle_func=lambda input:
                     morning_convo_state_match(input, 0) and
                    is_intent_name("AMAZON.YesIntent")(input))
def morning_yes_handler(handler_input):
    """Handler for Yes Intent, only if the player said yes to be asked morning questions
    """
    # type: (HandlerInput) -> Response
    attr = handler_input.attributes_manager.session_attributes
    
    st = "Good to hear."
    # Collect next prompt in branching conversation
    speech_text, reprompt = get_next_morning_prompt(attr)

    speech_text = (st + speech_text)
    handler_input.response_builder.speak(speech_text).ask(reprompt)
    
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=lambda input:
                    morning_convo_state_match(input, 0) and
                    is_intent_name("AMAZON.NoIntent")(input))
def morning_no_handler(handler_input):
    """Handler for No Intent, only if the player said no to be asked morning questions
    """
    # type: (HandlerInput) -> Response
    session_attr = handler_input.attributes_manager.session_attributes
    attr['morning_convo_state'] = -10
    
    handler_input.attributes_manager.persistent_attributes = session_attr
    handler_input.attributes_manager.save_persistent_attributes()

    speech_text = "Okay, no problem. Let Cookie know when you want to talk again. Have a good rest of your morning!!"

    handler_input.response_builder.speak(speech_text)
    return handler_input.response_builder.response


# ask the user if they have time to answer some questions 
# attr['morning_convo_state'] -1 --> 0
@sb.request_handler(can_handle_func=lambda input : 
                        morning_convo_state_match(input, -1) and 
                        is_intent_name("MorningInit")(input))
def Morning_Init_handler(handler_input):
    """Handler for MorningInit Launch.

    Get the session_attributes, to figure out the game state.
    """
    # type: (HandlerInput) -> Response
    attr = handler_input.attributes_manager.session_attributes

    speech_text = "Good morning {}. Do you have some time to answer some questions?".format(USER_NAME)
    attr['morning_convo_state'] = 0
    
    speech_text = (st)
    handler_input.attributes_manager.session_attributes = attr

    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func= lambda input : is_intent_name("MorningSleepResponse")(input) and
                            morning_convo_state_match(input, 1) )
def Morning_Sleep_Response_handler(handler_input):
    """Handler for MorningSleepResponse .

    Get the session_attributes, to figure out the game state.
    """
    # type: (HandlerInput) -> Response
    attr = handler_input.attributes_manager.session_attributes
    
    sleep_quality = int(handler_input.request_envelope.request.intent.slots["sleep_quality"]["resolutions"]["resolutionsPerAuthority"][0]["values"][0]["value"]["id"])
    # avg_q = 0
    # for quality in sleep_quality_vals:
    #     avg_q += int(quality["value"]["id"])
    # sleep_quality = avg_q / len(sleep_quality_vals)

    st = ""
    
    # if handler_input.request_envelope.request.intent.slots["sleep_quality"].value == "good":
    #     st += "I'm glad you slept well" 
    
    # attr['morning_convo_eplored'].append(attr['morning_convo_state'])
    # if len(attr['morning_convo_eplored']) != 4:
    #     next_convo_route = attr['morning_convo_state']
    #     while next_convo_route in attr['morning_convo_eplored']:
    #         next_convo_route = random.randint(0, 4)
    
    if sleep_quality > 0 :    
        st += "I'm glad to hear you slept well. "
    else:
        st += "I'm sorry to hear you slept poorly. "
    
    st2 , rp = get_next_morning_prompt(attr)
    
    speech_text = (st + st2)
    reprompt = rp 
    
    handler_input.attributes_manager.session_attributes = attr

    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response


# ----------------------------------------------------------------------------------------------------------- #
# ----------------------------------- MORNING CONVO END ----------------------------------------------------- #
# ----------------------------------------------------------------------------------------------------------- #










@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Handler for Help Intent."""
    # type: (HandlerInput) -> Response
    speech_text = (
        "I am thinking of a number between zero and one hundred, try to "
        "guess it and I will tell you if you got it or it is higher or "
        "lower")
    reprompt = "Try saying a number."

    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(
    can_handle_func=lambda input:
        is_intent_name("AMAZON.CancelIntent")(input) or
        is_intent_name("AMAZON.StopIntent")(input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for Cancel and Stop Intent."""
    # type: (HandlerInput) -> Response
    speech_text = "Thanks for playing!!"

    handler_input.response_builder.speak(
        speech_text).set_should_end_session(True)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for Session End."""
    # type: (HandlerInput) -> Response
    logger.info(
        "Session ended with reason: {}".format(
            handler_input.request_envelope.request.reason))
    return handler_input.response_builder.response


def currently_playing(handler_input):
    """Function that acts as can handle for game state."""
    # type: (HandlerInput) -> bool
    is_currently_playing = False
    session_attr = handler_input.attributes_manager.session_attributes

    if ("game_state" in session_attr
            and session_attr['game_state'] == "STARTED"):
        is_currently_playing = True

    return is_currently_playing

@sb.request_handler(can_handle_func=lambda input:
                    not currently_playing(input) and
                    is_intent_name("AMAZON.NoIntent")(input))
def no_handler(handler_input):
    """Handler for No Intent, only if the player said no for
    a new game.
    """
    # type: (HandlerInput) -> Response
    session_attr = handler_input.attributes_manager.session_attributes
    session_attr['game_state'] = "ENDED"
    session_attr['ended_session_count'] += 1

    handler_input.attributes_manager.persistent_attributes = session_attr
    handler_input.attributes_manager.save_persistent_attributes()

    speech_text = "Ok. See you next time!!"

    handler_input.response_builder.speak(speech_text)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=lambda input:
                    is_intent_name("AMAZON.FallbackIntent")(input) or
                    is_intent_name("AMAZON.YesIntent")(input) or
                    is_intent_name("AMAZON.NoIntent")(input))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    # type: (HandlerInput) -> Response
    session_attr = handler_input.attributes_manager.session_attributes

    if ("game_state" in session_attr and
            session_attr["game_state"]=="STARTED"):
        speech_text = (
            "The {} skill can't help you with that.  "
            "Try guessing a number between 0 and 100. ".format(SKILL_NAME))
        reprompt = "Please guess a number between 0 and 100."
    else:
        speech_text = (
            "The {} skill can't help you with that.  "
            "It will ".format(SKILL_NAME))
        reprompt = "Say yes to start the game or no to quit."

    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=lambda input: True)
def unhandled_intent_handler(handler_input):
    """Handler for all other unhandled requests."""
    # type: (HandlerInput) -> Response
    speech = "Say what kind of check in you would like to perform"
    handler_input.response_builder.speak(speech).ask(speech)
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    # type: (HandlerInput, Exception) -> Response
    logger.error(exception, exc_info=True)
    speech = "Sorry, I can't understand that. Please say again!!"
    handler_input.response_builder.speak(speech).ask(speech)
    return handler_input.response_builder.response


@sb.global_response_interceptor()
def log_response(handler_input, response):
    """Response logger."""
    # type: (HandlerInput, Response) -> None
    logger.info("Response: {}".format(response))


lambda_handler = sb.lambda_handler()
