from django_jinja import library


@library.filter
def leet_speak(input_str):
    charset = {"a": "4", "e": "3", "l": "1", "o": "0", "s": "5", "t": "7"}
    output_str = ""
    for char in input_str:
        output_str += charset.get(char.lower(), char)
    return output_str
