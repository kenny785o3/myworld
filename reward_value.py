import re
import json

month_targets = ["within the first (.*?) months", "within first (.*?) months", "in the first (.*?) months",
                 "within (.*?) months"]
day_targets = ["within the first (.*?) calendar days", "within first (.*?) calendar days", "within the first (.*?) days",
               "within the first (.*?) days", "within (.*?) days", "within first (.*?) calendar"]
duration_targets = ["within the first (.*?) months", "within first (.*?) months", "in the first (.*?) months",
                    "within (.*?) months", "within the first (.*?) calendar days", "within first (.*?) calendar days",
                    "within the first (.*?) days", "within the first (.*?) days", "within (.*?) days", "within first (.*?) calendar"]
spending_targets = ["spend over hk$/rmb(.*?) ", "instalment plan of first hk(.*?) ", "spending of hk(.*?) ",
                    "spend over hk(.*?) ", "amount of hk(.*?) ", "retail spending/cash advance of hk(.*?) ",
                    "retail spending of an equivalent of hk(.*?) ", "spending requirement: accumulate hk(.*?) ",
                    "spending requirement: hk(.*?) ", "spend hk(.*?) ", "designated merchants of hk(.*?) "]
unwanted_targets = ["automatically credited to", "will be credited to","existing credit card customer", "will be credited into"]


def dates_included(text):
    for target in duration_targets:
        if re.search(target, text.replace("\xa0", " ").lower()):
            return True
    return False


def spending_included(text):
    for target in spending_targets:
        if re.search(target, text.replace("\xa0", " ").lower()):
            return True
    return False


def unwanted_included(text):
    for target in unwanted_targets:
        if re.search(target, text.replace("\xa0", " ").lower()):
            return True
    return False


def condition_cleansing(conditions):
    clean_conditions = []
    for unclean_condition in conditions:
        if unwanted_included(unclean_condition.lower()):
            continue
        elif dates_included(unclean_condition.lower()) or spending_included(unclean_condition.lower()):
            clean_conditions.append(unclean_condition)
    return clean_conditions


def is_multi_reward(option):
    return option.find(" + ") != -1


def is_point(reward):
    p = reward.lower()
    target = ["point", "points", "cash dollars", "rewardcash"]
    return any(re.findall('|'.join(target), p))


def is_mile(reward):
    p = reward.lower()
    target = ["asia", "miles", "mile", "avios"]
    return any(re.findall('|'.join(target), p))


def is_cash_coupon(text):
    p = text.lower().replace(")"," ")
    targets = ["hk(.*?) cash", "hk(.*?) coupon", "hk(.*?) gift", "hk(.*?) rebate", "hk(.*?) promo", "hk(.*?) "]
    if re.search("cash instalment", p):
        return False
    for target in targets:
        if re.search(target, p):
            return True
    return False


def get_spending(text):
    text = text.lower().replace("\xa0", " ")
    for target in spending_targets:
        if re.search(target, text):
            g = re.search(target, text).group(1).split("$")[1]
            if not g.find("rmb") == -1:
                g = g.split("rmb")[1]
            return g


def get_month(text):
    num_dict = {
        'one': 1,
        'two': 2,
        'three': 3,
        'four': 4,
        'five': 5
    }
    for m, d in zip(month_targets, day_targets):
        if re.search(m, text.replace("\xa0", " ")):
            month = re.search(m, text.replace("\xa0", " ")).group(1)
            if month.isdigit():
                return month
            else:
                return num_dict[month]
        elif re.search(d, text.replace("\xa0", " ")):
            return int(int(re.search(d, text.replace("\xa0", " ")).group(1)) / 30)


def non_miles_and_point_condition_value(condition):
    spending = get_spending(condition)
    month = get_month(condition)
    return spending, month


def get_cash_option_value(reward):
    p = reward.lower().replace(")"," ").replace("("," ")
    return re.search("hk(.*?) ",p).group(1).split("$")[1]


def get_points_value(reward):
    p = reward.lower()
    if re.search("(.*?) rewardcash",p):
        return re.search("(.*?) rewardcash",p).group(1).split("$")[1]
    elif re.search("(.*?) cash dollars",p):
        return re.search("(.*?) cash dollars", p).group(1).split("$")[1]


def get_details(options):
    month = None
    tmp = []
    for option in options:
        is_cal = True
        ## Cleansing of conditions
        if not option:  # If there is no option for a card, continue to next option
            is_cal = False
            continue
        conditions = condition_cleansing(option["condition"]) # identify condition that have $ or month
        if not conditions: # If none of the conditions have $ or month, continue
            is_cal = False
            continue
        elif len(conditions) == 1 and (not spending_included(conditions[0]) or not dates_included(conditions[0])):
            # If there is only one condition which doesn't include both spending and month, continue
            is_cal = False
            continue
        rewards = []
        reward = option["option"]
        if is_multi_reward(reward):
            # print(f"Mulitple reward found in one option from {card['productName']}")
            rewards = reward.split("+")
        else:
            rewards.append(reward)
        details = []
        for i, splited_reward in enumerate(rewards):
            if not splited_reward.lower().find("redemption fee") == -1:
                is_cal = False
            elif is_mile(splited_reward):
                is_cal = False
            elif is_cash_coupon(splited_reward):  # It is a cash/coupon reward
                #print(f"{card['productName']} \n{key} \nCash \n{splited_reward}")
                #print(conditions)
                option_value = get_cash_option_value(splited_reward)
                if len(conditions) == len(rewards):
                    spending, month = non_miles_and_point_condition_value(conditions[i])
                    details.append({
                        'option_value':option_value,
                        'required_spending':spending
                    })
                elif len(rewards) == 1 and len(conditions) > 1:
                    spending, month = non_miles_and_point_condition_value(conditions[0])
                    details.append({
                        'option_value':option_value,
                        'required_spending':spending
                    })
            elif is_point(splited_reward):
                option_value = get_points_value(splited_reward)
                if len(conditions) == len(rewards):
                    spending, month = non_miles_and_point_condition_value(conditions[i])
                    details.append({
                        'option_value': option_value,
                        'required_spending': spending
                    })
                elif len(conditions) == 1 and len(rewards) > 1:
                    spending, month = non_miles_and_point_condition_value(conditions[0])
                    details.append({
                        'option_value': option_value,
                        'required_spending': spending
                    })
            else:  # Is item
                if re.search("value at hk(.*?)", splited_reward.lower()) or \
                        not splited_reward.lower().find("reference retail price") == -1:
                    continue
                else:
                    is_cal = False
                    continue
        tmp.append({
            'option': reward,
            'condition': option["condition"],
            'is_cal':is_cal,
            'details':details,
            'number_of_month':month
        })
    return tmpe
