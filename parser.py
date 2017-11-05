import yaml

class ExceptionInvalidTheoFile(Exception):
    pass

class ParserYaml(object):

    def __init__(self, path):
        self.path = path

    def process(self):

        with open(self.path, 'r') as testfile:
            content = testfile.readlines()

        content = self.search_theo(content)

        try:
            dictionary = yaml.load(content)
        except:
            raise ExceptionInvalidTheoFile()

        if not 'configuration' in dictionary:
            dictionary['configuration'] = dict()

        return dictionary

    def search_theo(self, data):
        '''Try to find a !theo block. If not found, get all the file.'''
        start = None
        end = None

        for lineno, line in enumerate(data):
            if '!theo' in line:
                if start == None:
                    start = lineno
                else:
                    end = lineno

        if start != None and end != None:
            i = data[start].index('!theo')
            prev = data[start][0:i]
            prevlen = len(prev)
            prev = prev.rstrip()

            contents = ''

            for line in data[start+1:end]:
                if not line.startswith(prev):
                    return
                cropped = line[prevlen:] or '\n'
                contents += cropped

            return contents
        else:
            return ''.join(data)

