/** 台账列表与详情页之间的刷新信号。

列表页被 keep-alive 缓存：从详情页浏览返回时保留筛选条件、分页和滚动位置；
但如果在详情页真的执行了动作，列表数据需要刷新。详情页动作成功后 bump()，
列表页 onActivated 时 consumeChanged() 判断是否重新拉取。
 */
import { ref } from 'vue'

const revision = ref(0)

export const adoptListRevision = {
  bump() {
    revision.value += 1
  },
  consumeChanged(): boolean {
    return revision.value > 0 ? (revision.value = 0, true) : false
  },
}
