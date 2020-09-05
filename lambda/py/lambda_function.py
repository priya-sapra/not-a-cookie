# -*- coding: utf-8 -*-
"""cookie sample app."""

import random
import logging
import json
import prompts
import os
import boto3

# from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractExceptionHandler,
    AbstractRequestInterceptor, AbstractResponseInterceptor)

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.ui import SimpleCard
from ask_sdk_model import Response
from ask_sdk_s3.adapter import S3Adapter

SKILL_NAME = 'High Low Game'
bucket_name = os.environ.get('S3_PERSISTENCE_BUCKET')
s3_client = boto3.client('s3',
                         region_name=os.environ.get('S3_PERSISTENCE_REGION'),
                         config=boto3.session.Config(signature_version='s3v4',s3={'addressing_style': 'path'}))
s3_adapter = S3Adapter(bucket_name=bucket_name, path_prefix="Media", s3_client=s3_client)
sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def currently_playing(handler_input):
    """Function that acts as can handle for game state."""
    # type: (HandlerInput) -> bool
    is_currently_playing = False
    session_attr = handler_input.attributes_manager.session_attributes

    if ("game_state" in session_attr
            and session_attr['game_state'] == "STARTED"):
        is_currently_playing = True

    return is_currently_playing

# Built-in Intent Handlers
class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch.

    Get the persistence attributes, to figure out the game state.
    """
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        attr = handler_input.attributes_manager.persistent_attributes
        if not attr:
            attr['ended_session_count'] = 0
            attr['games_played'] = 0
            attr['game_state'] = 'ENDED'

        handler_input.attributes_manager.session_attributes = attr

        speech_text = (
            "Welcome to the High Low guessing game. You have played {} times. "
            "Would you like to play?".format(attr["games_played"]))
        reprompt = "Say yes to start the game or no to quit."

        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response

        
class YesHandler(AbstractRequestHandler):
    """Handler for Yes Intent, only if the player said yes for a new game."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> Bool
        return not currently_playing(handler_input) and is_intent_name("AMAZON.YesIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['game_state'] = "STARTED"
        session_attr['guess_number'] = random.randint(0, 100)
        session_attr['no_of_guesses'] = 0

        speech_text = "Great! Try saying a number to start the game."
        reprompt = "Try saying a number."

        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response


class NoHandler(AbstractRequestHandler):
    """Handler for No Intent, only if the player said no for a new game."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> Bool
        return not currently_playing(handler_input) and is_intent_name("AMAZON.NoIntent")(handler_input)

    def handle(self, handler_input):
         # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['game_state'] = "ENDED"
        session_attr['ended_session_count'] += 1

        handler_input.attributes_manager.persistent_attributes = session_attr
        handler_input.attributes_manager.save_persistent_attributes()

        speech_text = "Ok. See you next time!!"

        handler_input.response_builder.speak(speech_text)
        return handler_input.response_builder.response


class NumberGuesserHandler(AbstractRequestHandler):
    """Handler for processing guess with target."""
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return currently_playing(handler_input) and is_intent_name("NumberGuessIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        target_num = session_attr["guess_number"]
        guess_num = int(handler_input.request_envelope.request.intent.slots[
            "number"].value)

        session_attr["no_of_guesses"] += 1

        if guess_num > target_num:
            speech_text = (
                "{} is too high. Try saying a smaller number.".format(guess_num))
            reprompt = "Try saying a smaller number."
        elif guess_num < target_num:
            speech_text = (
                "{} is too low. Try saying a larger number.".format(guess_num))
            reprompt = "Try saying a larger number."
        elif guess_num == target_num:
            speech_text = (
                "Congratulations. {} is the correct guess. "
                "You guessed the number in {} guesses. "
                "Would you like to play a new game?".format(
                    guess_num, session_attr["no_of_guesses"]))
            reprompt = "Say yes to start a new game or no to end the game"
            session_attr["games_played"] += 1
            session_attr["game_state"] = "ENDED"

            handler_input.attributes_manager.persistent_attributes = session_attr
            handler_input.attributes_manager.save_persistent_attributes()
        else:
            speech_text = "Sorry, I didn't get that. Try saying a number."
            reprompt = "Try saying a number."

        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response


# class GetNewFactHandler(AbstractRequestHandler):
#     """Handler for Skill Launch and GetNewFact Intent."""

#     def can_handle(self, handler_input):
#         # type: (HandlerInput) -> bool
#         return (is_request_type("LaunchRequest")(handler_input) or
#                 is_intent_name("GetNewFactIntent")(handler_input))

#     def handle(self, handler_input):
#         # type: (HandlerInput) -> Response
#         logger.info("In GetNewFactHandler")

#         # get localization data
#         data = handler_input.attributes_manager.request_attributes["_"]

#         random_fact = random.choice(data[prompts.FACTS])
#         speech = data[prompts.GET_FACT_MESSAGE].format(random_fact)

#         handler_input.response_builder.speak(speech).set_card(
#             SimpleCard(data[prompts.SKILL_NAME], random_fact))
#         return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = (
        "I am thinking of a number between zero and one hundred, try to "
        "guess it and I will tell you if you got it or it is higher or "
        "lower")
        reprompt = "Try saying a number."

        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = "Thanks for playing!!"

        handler_input.response_builder.speak(
            speech_text).set_should_end_session(True)
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent.

    AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input) or 
        is_intent_name("AMAZON.YesIntent")(handler_input) or 
        is_intent_name("AMAZON.NoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")

        # get localization data
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
                "It will come up with a number between 0 and 100 and "
                "you try to guess it by saying a number in that range. "
                "Would you like to play?".format(SKILL_NAME))
            reprompt = "Say yes to start the game or no to quit."

        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response


class LocalizationInterceptor(AbstractRequestInterceptor):
    """
    Add function to request attributes, that can load locale specific data.
    """

    def process(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        logger.info("Locale is {}".format(locale[:2]))

        # localized strings stored in language_strings.json
        with open("language_strings.json") as language_prompts:
            language_data = json.load(language_prompts)
        # set default translation data to broader translation
        data = language_data[locale[:2]]
        # if a more specialized translation exists, then select it instead
        # example: "fr-CA" will pick "fr" translations first, but if "fr-CA" translation exists,
        #          then pick that instead
        if locale in language_data:
            data.update(language_data[locale])
        handler_input.attributes_manager.request_attributes["_"] = data


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In SessionEndedRequestHandler")

        logger.info("Session ended reason: {}".format(
            handler_input.request_envelope.request.reason))
        return handler_input.response_builder.response


# Exception Handler
class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler, log exception and
    respond with custom message.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.info("In CatchAllExceptionHandler")
        logger.error(exception, exc_info=True)

        handler_input.response_builder.speak(EXCEPTION_MESSAGE).ask(
            HELP_REPROMPT)

        return handler_input.response_builder.response


# Request and Response loggers
class RequestLogger(AbstractRequestInterceptor):
    """Log the alexa requests."""

    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug("Alexa Request: {}".format(
            handler_input.request_envelope.request))


class ResponseLogger(AbstractResponseInterceptor):
    """Log the alexa responses."""

    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.debug("Alexa Response: {}".format(response))


# Register intent handlers
sb.add_request_handler(GetNewFactHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Register exception handlers
sb.add_exception_handler(CatchAllExceptionHandler())

# Register request and response interceptors
sb.add_global_request_interceptor(LocalizationInterceptor())
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

# Handler name that is used on AWS lambda
lambda_handler = sb.lambda_handler()
