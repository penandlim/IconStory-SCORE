from iconservice import *

TAG = 'IconStoryOnline'

MICRO_SECONDS = 1000000
SECONDS_IN_DAY = 86400
DECIMAL = 10 ** 18
DECIMAL_CTRL_POINT = 3
DECIMAL_CTRL = 10 ** DECIMAL_CTRL_POINT
DEFAULT_FG = b'\xff\xff\xff'
DEFAULT_BG = b'\x00\x00\x00'


class IconStoryOnline(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._removingAllowed = VarDB('removingAllowed', db, value_type=bool)
        self._fancywordAmount = VarDB('fancywordAmount', db, value_type=int)
        self._defaultFG = VarDB('defaultFG', db, value_type=bytes)
        self._defaultBG = VarDB('defaultBG', db, value_type=bytes)
        self._storySize = DictDB('storySize', db, value_type=int)
        self._story = DictDB('story', db, value_type=str, depth=2)
        self._storyValue = DictDB('storyValue', db, value_type=int, depth=2)
        self._styleFG = DictDB('styleFG', db, value_type=bytes, depth=2)
        self._styleBG = DictDB('styleBG', db, value_type=bytes, depth=2)
        self._storyOwner = DictDB('storyOwner', db, value_type=Address, depth=2)

    def on_install(self) -> None:
        super().on_install()
        self._removingAllowed.set(False)
        self._fancywordAmount.set(1 * DECIMAL)
        self._defaultFG.set(DEFAULT_FG)
        self._defaultBG.set(DEFAULT_BG)
        

    def on_update(self) -> None:
        super().on_update()

    def _roundTimeToDay(self, datetime: int) -> int:
        if (datetime < 0):
            revert("Datetime is negative.")
        return datetime - (datetime % SECONDS_IN_DAY)

    def _getNowRoundToDay(self) -> int:
        time_in_seconds = int(self.now() / MICRO_SECONDS)
        date = self._roundTimeToDay(time_in_seconds)
        return date

    def _checkOwner(self) -> None:
        if self.msg.sender != self.owner:
            revert("Only the contract owner can call this function!")
            
    def _checkAddressIsUser(self, addressToCheck: Address):
        if (addressToCheck.is_contract):
            revert("You cannot use this service with a SCORE!")
            
    @eventlog
    def setWordLog(self, word_index: int, word: str, owner_address: Address):
        pass

    @external(readonly=True)
    def getRemovingAllowed(self) -> bool:
        return self._removingAllowed.get()

    @external(readonly=False)
    def setRemovingAllowed(self, isAllowed: bool) -> None:
        self._checkOwner()
        self._removingAllowed.set(isAllowed)

    @external(readonly=True)
    def getFancywordsAmount(self) -> int:
        return self._fancywordAmount.get()

    @external(readonly=False)
    def setFancywordsAmount(self, amount: int) -> None:
        self._checkOwner()
        if amount < DECIMAL / 100:
            revert("Set too low!")
        self._fancywordAmount.set(amount)

    @external(readonly=True)
    def getDefaultFG(self) -> bytes:
        return self._defaultFG.get()

    @external(readonly=False)
    def setDefaultFG(self, default_fg: bytes) -> None:
        self._checkOwner()
        self._defaultFG.set(default_fg)

    @external(readonly=True)
    def getDefaultBG(self) -> bytes:
        return self._defaultBG.get()

    @external(readonly=False)
    def setDefaultBG(self, default_bg: bytes) -> None:
        self._checkOwner()
        self._defaultBG.set(default_bg)

    @external(readonly=True)
    def getStoryOfDate(self, date: int) -> dict:
        date = self._roundTimeToDay(date)
        size = self._storySize[date]
        story = {}
        storyOwner = {}
        storyValue = {}
        styleFG = {}
        styleBG = {}
        for x in range(0, size):
            story[x] = self._story[date][x]
            storyOwner[x] = self._storyOwner[date][x].to_bytes()
            storyValue[x] = self._storyValue[date][x]
            styleFG[x] = self._styleFG[date][x]
            styleBG[x] = self._styleBG[date][x]

        return dict(story=story, storyOwner=storyOwner, storyValue=storyValue, styleFG=styleFG, styleBG=styleBG)

    @external(readonly=True)
    def getWord(self, word_index: int) -> dict:
        date = self._getNowRoundToDay()
        size = self._storySize[date]
        if (word_index > size):
            word_index = size - 1
        if (word_index < 0):
            word_index = 0
        return dict(word=self._story[date][word_index],
                        wordOwner=self._storyOwner[date][word_index],
                        wordValue=self._storyValue[date][word_index],
                        wordFG=self._styleFG[date][word_index],
                        wordBG=self._styleBG[date][word_index])

    @external(readonly=True)
    def getCurrentStory(self) -> dict:
        return self.getStoryOfDate(self._getNowRoundToDay())

    @external(readonly=True)
    def getStoryInRange(self, fromTimestamp: int, toTimestamp: int) -> dict:
        fromTime = self._roundTimeToDay(fromTimestamp)
        toTime = self._roundTimeToDay(toTimestamp)
        if (fromTime < toTime - SECONDS_IN_DAY * 60):
            fromTime = toTime - SECONDS_IN_DAY * 60
        storyDict = {}
        while fromTime <= toTime:
            storyDict[fromTime] = self.getStoryOfDate(fromTime)
            fromTime += SECONDS_IN_DAY
        return storyDict

    def _setWord(self, date_to_edit: int, word_index: int, word: str, style_fg: bytes, style_bg: bytes, writer: Address,
                 word_value: int) -> None:
        self._story[date_to_edit][word_index] = word
        self._storyOwner[date_to_edit][word_index] = writer
        self._storyValue[date_to_edit][word_index] = word_value
        self._styleFG[date_to_edit][word_index] = style_fg
        self._styleBG[date_to_edit][word_index] = style_bg
        self.setWordLog(word_index, word, writer)

    def _removeWord(self, date_to_edit: int, word_index: int) -> None:
        current_story_size = self._storySize[date_to_edit]
        
        if (current_story_size < 1):
            revert("You cannot remove from an empty story.")

        for i in range(word_index, current_story_size - 1):
            self._setWord(date_to_edit, i, self._story[date_to_edit][i + 1], self._styleFG[date_to_edit][i + 1],
                          self._styleBG[date_to_edit][i + 1], self._storyOwner[date_to_edit][i + 1],
                          self._storyValue[date_to_edit][i + 1])
        self._setWord(date_to_edit, current_story_size - 1, "", self._defaultFG.get(), self._defaultBG.get(), self.owner, 0)
        self._storySize[date_to_edit] -= 1

    @payable
    @external(readonly=False)
    def removeWordToday(self, word_index: int) -> None:
        self.removeWord(self._getNowRoundToDay(), word_index)

    @payable
    @external(readonly=False)
    def removeWord(self, date_to_edit: int, word_index: int) -> None:
        self._checkAddressIsUser(self.msg.sender)
        date_to_edit = self._roundTimeToDay(date_to_edit)
        if word_index < 0 or word_index >= self._storySize[date_to_edit]:
            revert("You cannot remove a non-existing word.")
        if self.msg.sender == self.owner:
            self._removeWord(date_to_edit, word_index)
        else:
            if self._removingAllowed.get():
                if self.msg.value < ((self._storyValue[date_to_edit][word_index] * 110) / 100):
                    need = float(((self._storyValue[date_to_edit][word_index] * 110) / 100) / DECIMAL)
                    revert(f"Need {need} or more ICX to remove the word.")
                else:
                    self.icx.transfer(self._storyOwner[date_to_edit][word_index],
                                      (self._storyValue[date_to_edit][word_index] * 107) / 100)
                    self._removeWord(date_to_edit, word_index)
            else:
                revert("Removing words are not allowed currently.")

    @payable
    def setWord(self, word_index: int, word: str, style_fg: bytes, style_bg: bytes, insert: bool) -> None:
        writer = self.msg.sender
        
        self._checkAddressIsUser(self.msg.sender)

        # Check for empty or long words
        word = ''.join(word.split())
        if word == "":
            revert("You cannot write an empty word.")
        if len(word) > 16:
            revert(f"Your word cannot be longer than 16 characters! Given: {word}")

        # Check and fix word_index.
        if word_index < 0:
            word_index = 0
            insert = True

        date_to_edit = self._getNowRoundToDay()

        current_story_size = self._storySize[date_to_edit]

        if current_story_size > 15:
            revert("You cannot write more.")

        if word_index > current_story_size:
            word_index = current_story_size
        current_word = self._story[date_to_edit][word_index]

        if current_word == "":
            # No word exists in current position.
            if self.msg.value < self._fancywordAmount.get():
                self._setWord(date_to_edit, word_index, word, self._defaultFG.get(), self._defaultBG.get(), writer, 0)
            else:
                self._setWord(date_to_edit, word_index, word, style_fg, style_bg, writer, self.msg.value)
            self._storySize[date_to_edit] += 1

        else:
            if insert:

                # Needs to shift everything by one
                for i in reversed(range(word_index, current_story_size)):
                    self._setWord(date_to_edit, i + 1, self._story[date_to_edit][i], self._styleFG[date_to_edit][i],
                                  self._styleBG[date_to_edit][i], self._storyOwner[date_to_edit][i],
                                  self._storyValue[date_to_edit][i])

                if self.msg.value < self._fancywordAmount.get():
                    self._setWord(date_to_edit, word_index, word, self._defaultFG.get(), self._defaultBG.get(), writer, 0)
                else:
                    self._setWord(date_to_edit, word_index, word, style_fg, style_bg, writer, self.msg.value)
                self._storySize[date_to_edit] += 1

            else:

                # Sender wants to replace existing word
                # Check if amount is enough.
                story_value = self._storyValue[date_to_edit][word_index]
                if story_value == 0:
                    if self.msg.value < self._fancywordAmount.get():
                        need = float(self._fancywordAmount.get() / DECIMAL)
                        revert(
                            f"Need {need} ICX or more to replace the word. Given {self.msg.value} but needed {self._fancywordAmount.get()}")
                if self.msg.value < (story_value * 110) / 100:
                    need = float(((story_value * 110) / 100) / DECIMAL)
                    revert(f"Need {need} ICX or more to replace the word. Given {self.msg.value} but needed {(story_value * 110) / 100}")

                # Sender's value is higher than current story value. Check if story value is positive and if it is, transfer appropriate ICX.
                if story_value > 0:
                    self.icx.transfer(self._storyOwner[date_to_edit][word_index], int((story_value * 107) / 100))

                self._setWord(date_to_edit, word_index, word, style_fg, style_bg, writer, int(self.msg.value))

    @payable
    @external(readonly=False)
    def addNormalWord(self, word_index: int, word: str) -> None:
        self.setWord(word_index, word, self._defaultFG.get(), self._defaultBG.get(), True)

    @payable
    @external(readonly=False)
    def addFancyWord(self, word_index: int, word: str, style_fg: bytes, style_bg: bytes) -> None:
        self.setWord(word_index, word, style_fg, style_bg, True)

    @payable
    @external(readonly=False)
    def replaceWord(self, word_index: int, word: str, style_fg: bytes, style_bg: bytes) -> None:
        self.setWord(word_index, word, style_fg, style_bg, False)

    @payable
    def fallback(self) -> None:
        Logger.info('Fallback is called', TAG)

    @external(readonly=False)
    def withdraw(self) -> None:
        self._checkOwner()
        self.icx.transfer(self.owner, self.icx.get_balance(self.address))
