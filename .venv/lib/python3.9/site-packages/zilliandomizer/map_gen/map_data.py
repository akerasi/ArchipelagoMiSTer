from .base_maker import Node


red_right_no_doors = {
    Node(0, 2),  # no computer  # TODO: implement changing which rooms have computers and doors?
    Node(0, 3),  # start hall
    Node(1, 2),  # hall
    Node(2, 1),  # no computer and no canisters
    Node(4, 3),  # hall
    Node(4, 4),  # no canisters
}
""" the nodes in red right that don't have keywords to open doors """

pc_no_doors = {
    Node(0, 0), Node(1, 0), Node(2, 0), Node(3, 0), Node(4, 0), Node(5, 0), Node(6, 0),  # left
    Node(0, 1), Node(1, 1), Node(2, 1),             Node(4, 1), Node(5, 1), Node(6, 1),  # rooms and halls
    Node(0, 7), Node(1, 7), Node(2, 7), Node(3, 7), Node(4, 7), Node(5, 7), Node(6, 7),  # right
    Node(0, 5), Node(0, 6),  # main computer
    Node(6, 3), Node(6, 4), Node(6, 5), Node(6, 6),  # bottom hall
}
""" the nodes in paperclip that don't have keywords to open doors """
