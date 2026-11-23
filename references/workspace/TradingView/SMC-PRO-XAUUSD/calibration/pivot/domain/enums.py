from enum import Enum

class PivotProfileFamily(str, Enum): SI="SI"; SE="SE"; WI="WI"; WE="WE"
class PivotDirection(str, Enum): HIGH="HIGH"; LOW="LOW"
class CandidateStatus(str, Enum): ACTIVE="ACTIVE"; REPLACED="REPLACED"; INVALIDATED="INVALIDATED"; COMMITTED="COMMITTED"
