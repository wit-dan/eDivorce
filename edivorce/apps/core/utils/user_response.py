from edivorce.apps.core.models import UserResponse, Question
from edivorce.apps.core.utils.question_step_mapping import question_step_mapping

def get_responses_from_db(bceid_user):
    """ Get UserResponses from the database for a user. """
    married, married_questions, responses = __get_data(bceid_user)
    responses_dict = {}
    for answer in responses:
        if not married and answer.question_id in married_questions:
            responses_dict[answer.question.key] = ''
        else:
            responses_dict[answer.question.key] = answer.value

    return responses_dict


def get_responses_from_db_grouped_by_steps(bceid_user):
    """ Group questions and responses by steps they belong to """
    married, married_questions, responses = __get_data(bceid_user)
    responses_dict = {}

    for step, questions in question_step_mapping.items():

        lst = []
        step_responses = responses.filter(question_id__in=questions).exclude(
            value__in=['', '[]', '[["",""]]']).order_by('question')

        for answer in step_responses:
            if not married and answer.question_id in married_questions:
                value = ''
            else:
                value = answer.value

            lst += [{'question__conditional_target': answer.question.conditional_target,
                     'question__reveal_response': answer.question.reveal_response,
                     'value': value,
                     'question__name': answer.question.name,
                     'question__required': answer.question.required,
                     'question_id': answer.question.pk}]

        responses_dict[step] = lst

    return responses_dict


def get_responses_from_session(request):
    return sorted(request.session.items())


def get_responses_from_session_grouped_by_steps(request):
    question_list = Question.objects.filter(key__in=question_step_mapping['prequalification'])

    lst = []

    for question in question_list:
        lst += [{'question__conditional_target': question.conditional_target,
                 'question__reveal_response': question.reveal_response,
                 'value': request.session.get(question.pk, ''),
                 'question__name': question.name,
                 'question__required': question.required,
                 'question_id': question.pk}]

    return {'prequalification': lst}


def save_to_db(serializer, question, value, bceid_user):
    """ Saves form responses to the database """
    data = {'bceid_user': bceid_user,
            'question': question,
            'value': value}
    try:
        instance = UserResponse.objects.get(bceid_user=bceid_user, question=question)
        serializer.update(instance=instance, validated_data=data)
    except UserResponse.DoesNotExist:
        serializer.create(validated_data=data)


def save_to_session(request, question, value):
    """ Saves prequalifying responses to the user's session """
    request.session[question.pk] = value


def copy_session_to_db(request, bceid_user):
    """ Copies responses to pre-qualification questions from the user's session to the db """
    questions = Question.objects.all()

    for q in questions:
        if request.session.get(q.key) is not None:
            # copy the response to the database
            UserResponse.objects.update_or_create(
                bceid_user=bceid_user,
                question=q,
                defaults={'value': request.session.get(q.key)},
            )

            # clear the response from the session
            request.session[q.key] = None


def __get_data(bceid_user):
    """
    Gets UserResponses from the database for a user, plus a boolean indicating
    if the user is married or common-law, and a list of questions that only apply to
    married couples
    """
    COMMON_LAW = 'Living together in a marriage like relationship'
    MARRIED = 'Legally married'

    responses = UserResponse.objects.filter(bceid_user=bceid_user)
    married = responses.get(question_id='married_marriage_like').value != COMMON_LAW
    married_questions = list(
        Question.objects.filter(reveal_response=MARRIED).values_list("key", flat=True))
    return married, married_questions, responses
