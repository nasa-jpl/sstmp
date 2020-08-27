export const arrayToObject = (arr) => {
    const obj = {}
    arr.map((el) => obj[el.name] = el.value)
    return obj
}