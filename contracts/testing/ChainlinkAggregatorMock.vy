#pragma version 0.3.10
"""
@notice Chainlink Aggregator Mock for testing
"""

decimals: public(uint256)
latestRound: public(uint80)

round_data: HashMap[uint80, RoundData]


struct RoundData:
    round_id: uint80
    answer: int256
    started_at: uint256
    updated_at: uint256
    answered_in_round: uint80

struct SetRoundData:
    answer: int256
    seconds_ago: uint256
    is_new_phase: bool


@payable
@external
def __init__(decimals: uint256, answer: int256):
    """
    @dev `answer` is adjusted by 10**decimals
    """
    self.decimals = decimals
    self.round_data[0].answer = answer * convert(10**decimals, int256)


@view
@external
def latestRoundData() -> RoundData:
    """
    @dev If no rounds were set, returns a valid roundId and sets updatedAt as block.timestamp.
         If one or more rounds have been set, returns the latest one.
    """
    latest_round: uint80 = self.latestRound
    r: RoundData = self.round_data[latest_round]
    if latest_round == 0:
        round_id: uint80 = convert(block.timestamp, uint80) + (1 << 64)
        r.round_id = round_id
        r.answered_in_round = round_id
    if r.updated_at == 0:
        r.started_at = block.timestamp
        r.updated_at = block.timestamp
    return r


@view
@external
def getRoundData(round_id: uint80) -> RoundData:
    """
    @dev Only returns rounds that were previously set with `batch_setRoundData`
    """
    assert round_id >= 1 << 64, "ChainlinkMock: Invalid round_id"
    r: RoundData = self.round_data[round_id]
    if r.round_id == 0:
        raise "ChainlinkMock: Unknown Round"
    return r


@external
def set_price(answer: int256):
    """
    @dev `answer` is adjusted by 10**decimals
    """
    latest_round: uint80 = self.latestRound
    self.round_data[latest_round].answer = answer * convert(10**self.decimals, int256)


@external
def set_updated_at(updated_at: uint256):
    latest_round: uint80 = self.latestRound
    self.round_data[latest_round].started_at = updated_at
    self.round_data[latest_round].updated_at = updated_at


@external
def batch_add_rounds(round_data: DynArray[SetRoundData, 1024]):
    """
    @dev All round answers are adjusted by 10**decimals
    """
    round_id: uint80 = self.latestRound
    if round_id == 0:
        round_id = (1 << 64) - 1

    for r in round_data:
        updated_at: uint256 = block.timestamp - r.seconds_ago
        assert self.round_data[round_id].updated_at < updated_at, "ChainlinkMock: bad seconds_ago"

        if r.is_new_phase:
            round_id = convert(((convert(round_id, uint256) >> 64) + 1) << 64, uint80)
        else:
            round_id += 1

        self.round_data[round_id] = RoundData({
            round_id: round_id,
            answer: r.answer * convert(10**self.decimals, int256),
            started_at: updated_at,
            updated_at: updated_at,
            answered_in_round: round_id
        })

    self.latestRound = round_id



@external
def add_round(answer: int256, is_new_phase: bool = False):
    """
    @dev `answer` is adjusted by 10**decimals
    """
    round_id: uint80 = self.latestRound + 1
    if round_id == 1:
        round_id = 1 << 64
    elif is_new_phase:
        round_id = convert(((convert(round_id, uint256) >> 64) + 1) << 64, uint80)

    self.round_data[round_id] = RoundData({
        round_id: round_id,
        answer: answer * convert(10**self.decimals, int256),
        started_at: block.timestamp,
        updated_at: block.timestamp,
        answered_in_round: round_id
    })

    self.latestRound = round_id
