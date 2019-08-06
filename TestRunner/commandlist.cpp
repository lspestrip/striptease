#include "commandlist.hpp"
#include <QDebug>
#include <QFont>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QVariantMap>

QString commandTypeToStr(CommandType type)
{
    switch (type) {
    case CommandType::Command:
        return QString("Command");
    case CommandType::Log:
        return QString("Log");
    case CommandType::Tag:
        return QString("Tag");
    default:
        return QString("Invalid");
    }
}

// Create a textual representation of the command, to be
// shown in the table within the main window.
QString commandToStr(const Command & cmd)
{
    const QVariantMap &parameters = cmd.parameters;

    if (parameters.contains("base_addr")) {
        QString descr = parameters["base_addr"].toString();
        if (parameters.contains("pol")) {
            descr += QString(" (%1)").arg(parameters["pol"].toString());
        }

        return descr;
    } else if (parameters.contains("tag")) {
        QString tagName = parameters["tag"].toString();
        if (parameters.contains("type") && parameters["type"] == "STOP") {
            tagName += " (stop)";
        } else {
            tagName += " (start)";
        }
        return tagName;
    } else if (parameters.contains("message")) {
        return parameters["message"].toString();
    } else {
        return QString("");
    }
}

QDebug operator<<(QDebug debug, const Command &c)
{
    QDebugStateSaver saver(debug);

    debug.nospace() << "Command(" << commandToStr(c) << ")";

    return debug;
}

CommandList::CommandList(QObject *parent)
    : QAbstractTableModel(parent)
{
}

void CommandList::resetTimes()
{
    emit beginResetModel();

    for(auto & curCommand : command_list) {
        curCommand.time = QDateTime();
    }

    emit endResetModel();
}

void CommandList::loadFromJson(const QString & s)
{
    QJsonDocument data = QJsonDocument::fromJson(s.toLocal8Bit());

    if(! data.isArray()) {
        throw QString("JSON data is not an array");
    }

    command_list.clear();
    if (data.isEmpty() || data.isNull())
        return;

    QJsonArray array = data.array();
    command_list.reserve(array.size());

    int idx{1};
    for(auto elem : array) {
        if (! elem.isObject()) {
            throw QString("Element %1 is not an object").arg(idx);
        }

        QJsonObject curObject = elem.toObject();
        CommandType curType;

        if (! curObject.contains("kind")) {
            curType = CommandType::None;
        } else {
            auto kindString = curObject["kind"];
            if (kindString == "command") {
                curType = CommandType::Command;
            } else if (kindString == "log") {
                curType = CommandType::Log;
            } else if (kindString == "tag") {
                curType = CommandType::Tag;
            } else {
                curType = CommandType::None;
            }
        }

        if (! curObject.contains("path") || ! curObject.contains("command"))
            continue;

        Command cmd{
            QDateTime(),
            curType,
            curObject["path"].toString(),
            curObject["command"].toObject().toVariantMap(),
        };
        command_list.append(cmd);
        ++idx;
    }
}

QVariant CommandList::headerData(int section, Qt::Orientation orientation, int role) const
{
    if (role == Qt::DisplayRole && orientation == Qt::Horizontal) {
        switch (section) {
        case 0:
            return QString("Time");
        case 1:
            return QString("Type");
        case 2:
            return QString("Description");
        case 3:
            return QString("Data");
        }
    }
    return QVariant();
}

int CommandList::rowCount(const QModelIndex &) const
{
    return command_list.length();
}

int CommandList::columnCount(const QModelIndex &) const
{
    return 4;
}

QVariant CommandList::data(const QModelIndex &index, int role) const
{
    if (index.row() >= command_list.length() || index.row() < 0)
        return QVariant();

    if (role == Qt::DisplayRole) {
        const Command &cur_command = command_list[index.row()];
        const QVariantMap &parameters = cur_command.parameters;

        switch(index.column()) {
        case 0:
            return cur_command.time;

        case 1:
            return commandTypeToStr(cur_command.type);

        case 2:
            return commandToStr(cur_command);

        case 3:
            if (parameters.contains("data")) {
                QStringList values = parameters["data"].toStringList();
                return values.join(", ");
            }
            return QString("");

        default:
            return QString("");
        }
    }

    if (role == Qt::FontRole) {
        const Command &cur_command = command_list[index.row()];
        QFont font;

        switch(cur_command.type) {
        case CommandType::Log:
            font.setItalic(true);
            break;
        case CommandType::Tag:
            font.setBold(true);
            break;
        default:
            break;
        }

        return font;
    }

    return QVariant();
}

void CommandList::setCommandTime(int index, const QDateTime &datetime)
{
    command_list[index].time = datetime;

    emit dataChanged(
        createIndex(index, 0),
        createIndex(index, columnCount())
    );
}
