class InvalidTag(Exception):
  def __init__(self, tag):
    super().__init__("Invalid tag from " + tag)