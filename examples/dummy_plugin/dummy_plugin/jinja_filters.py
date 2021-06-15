from nautobot.extras.plugins import PluginJinjaFilter


class LeetSpeakJinjaFilter(PluginJinjaFilter):
    """
    Example of a PluginJinjaFilter converts an input string to "1337 5p34k".
    """

    filter_name = "leetspeak"

    def filter(self, input_str):
        charset = {"a": "4", "e": "3", "l": "1", "o": "0", "s": "5", "t": "7"}
        output_str = ""
        for char in input_str:
            output_str += charset.get(char.lower(), char)
        return output_str


jinja_filters = [LeetSpeakJinjaFilter]
