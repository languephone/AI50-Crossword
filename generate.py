import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # Remove any words in the domain that do not match the length of each variable
        for v in self.domains:
            for x in self.domains[v].copy():
                if len(x) != v.length:
                    self.domains[v].remove(x)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        change_flag = False

        # Define which letter x and y must match on
        intersection_index = self.crossword.overlaps[x, y]

        # Create set of y letters that x can match with
        compatible_y_values = {
            word_y[intersection_index[1]]
            for word_y in self.domains[y]
        }

        # For each word in x, check if the intersecting letter exists in any word in y
        for word_x in self.domains[x].copy():
            if word_x[intersection_index[0]] not in compatible_y_values:
                self.domains[x].remove(word_x)
                change_flag = True

        return change_flag

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            # Generate complete list of arcs
            arcs = []
            for x in self.crossword.variables:
                neighbors = self.crossword.neighbors(x)
                for y in neighbors:
                    arcs.append((x, y))

        # As long as the arc queue exists, revise domains
        while arcs:
            current_arc = arcs.pop()

            if self.revise(*current_arc):
                # If any domains are length 0, then no solution exists
                if len(self.domains[current_arc[0]]) == 0:
                    return False
                # If change has been made to a domain, need to revise neighbors
                for neighbor in self.crossword.neighbors(current_arc[0]):
                    # Don't include neighbor if it's part of the current arc
                    if neighbor != current_arc[1]:
                        arcs.append((current_arc[0], neighbor))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        # Check for key not existing and key having no value
        for variable in self.crossword.variables:
            if not assignment.get(variable) or not len(assignment.get(variable)) > 0:
                return False

        return True


    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        # Check values are distinct
        if len(set(assignment.values())) != len(assignment.values()):
            return False

        # Check values are correct length
        for variable in self.crossword.variables:
            if variable in assignment:
                if len(assignment[variable]) != variable.length:
                    return False

        # Check no conflicts
        # For each variable, get neighbors and check if the intersecting letter matches
        for variable in assignment:
            neighbors = self.crossword.neighbors(variable)
            for neighbor in neighbors:
                intersection_index = self.crossword.overlaps[variable, neighbor]
                if neighbor in assignment:
                    if assignment[variable][intersection_index[0]] != assignment[neighbor][intersection_index[1]]:
                        return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        ordered_domains = {}

        neighbors = self.crossword.neighbors(var)
        
        # Any variable in assignment already has a value, so shouldn’t be
        # counted when determining number of values ruled out
        for neighbor in neighbors.copy():
            if neighbor in assignment:
                neighbors.remove(neighbor)

        for domain in self.domains[var]:
            elimination_count = 0
            for neighbor in neighbors:
                intersection_index = self.crossword.overlaps[var, neighbor]
                for neighbor_domain in self.domains[neighbor]:
                    if domain[intersection_index[0]] != neighbor_domain[intersection_index[1]]:
                        elimination_count += 1
            ordered_domains[domain] = elimination_count

        return sorted(ordered_domains,
            key=lambda x: ordered_domains[x])


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        
        ordered_variables = {}

        for variable in self.crossword.variables:
            if variable not in assignment:
                ordered_variables[variable] = {
                    'domain': len(self.domains[variable]),
                    'degree': len(self.crossword.neighbors(variable))
                }

        # Sort by degree in reverse to establish order of highest degree
        highest_degree = sorted(ordered_variables,
            key=lambda x: ordered_variables[x]['degree'], reverse=True)

        # Sort the degree-sorted list by remaining values
        remaining_values = sorted(highest_degree,
            key=lambda x: ordered_variables[x]['domain'])

        return remaining_values[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # Check if assignment is complete
        if self.assignment_complete(assignment):
            return assignment

        # Get next variable to assign
        var = self.select_unassigned_variable(assignment)

        # Check if variable assignment fits specification
        for value in self.order_domain_values(var, assignment):
            assignment[var] = value
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                if result:
                    return result
                del assignment[var]
            else:
                del assignment[var]
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
