import unittest
from src.ESutils import EsConnection, start_es


class TestESconnection(unittest.TestCase):

    def test_improper_connection(self):
        print "Checks whether exception is raised when connection to ES is not properly established !"
        self.assertRaises(Exception, s=EsConnection({"host": "localhost", "port": 00}))
        print "BAD ONE."

    def test_index_creation(self):
        con = EsConnection({"host": "localhost", "port": 9200})
        self.assertRaises(Exception, con.createIndex("medical_info_extraction","discard"))
        self.assertRaises(Exception, con.createIndex("medical_info_extraction","keep"))
        print "not tested yet"

    def test_update(self):
        print "not tested yet"

if __name__ == '__main__':
    unittest.main()

# other useful tests:
# addTypeEqualityFunc(typeobj, function) to test if two objects of same type-class
# assertListEqual(list1, list2, msg=None)
# assertTupleEqual(tuple1, tuple2, msg=None)
